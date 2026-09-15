import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from accounts.roles import is_manager
from approvals.models import ApprovalRequest
from companies.models import Company
from crm.models import Notice, Task

from .models import Notification, PushOutbox

TASK_FIELDS = ("company_id", "assigned_to_id", "created_by_id", "title", "content", "status", "priority", "due_at")
NOTICE_FIELDS = ("company_id", "title", "body", "code")
APPROVAL_FIELDS = ("company_id", "status", "requested_by_id", "request_type", "category", "title", "note", "amount", "currency", "related_url")
APPROVAL_KINDS = ["approval_submitted", "approval_updated", "approval_approved", "approval_rejected", "approval_paid"]


def snapshot(instance, topic):
    return tuple(getattr(instance, name) for name in {"task": TASK_FIELDS, "notice": NOTICE_FIELDS, "approval": APPROVAL_FIELDS}[topic])


def company_users(company):
    return get_user_model().objects.filter(is_active=True).filter(
        Q(profile__companies=company) | Q(is_staff=True) | Q(is_superuser=True)
        | Q(groups__name=settings.GROUP_MANAGER)
    ).distinct()


@transaction.atomic
def record_change(topic, instance, actor, before=None, event_key=None):
    """Called in the same API transaction as save; failed requests create no inbox item.

    Admin/bulk imports do not call this hook and intentionally don't broadcast old data.
    A retrying caller can supply the same event_key; no provider/network calls here.
    """
    if not getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False):
        return
    if topic not in ("task", "notice", "approval"):
        raise ValueError("Unsupported notification topic")
    if before == snapshot(instance, topic):
        return
    event_key = event_key or uuid.uuid4().hex
    if topic == "task":
        # Legacy company-less tasks cannot be safely routed to a tenant.
        if not instance.company_id:
            return
        companies = Company.objects.filter(pk=instance.company_id, is_active=True)
        assigned = before is None or before[1] != instance.assigned_to_id
        kind = "task_assigned" if assigned else "task_updated"
    elif topic == "approval":
        companies = Company.objects.filter(pk=instance.company_id, is_active=True)
        if before is None:
            kind = "approval_submitted"
        elif before[1] != instance.status:
            kind = {"approved": "approval_approved", "rejected": "approval_rejected", "paid": "approval_paid"}.get(instance.status)
            if not kind:
                return
        else:
            kind = "approval_updated"
    else:
        companies = Company.objects.filter(is_active=True)
        if instance.company_id:
            companies = companies.filter(pk=instance.company_id)
        kind = "notice_published" if before is None else "notice_updated"
    for company in companies:
        recipients = company_users(company).exclude(pk=actor.pk)
        if topic == "task":
            recipients = recipients.filter(pk__in=[instance.assigned_to_id, instance.created_by_id])
        elif topic == "approval":
            if kind in ("approval_submitted", "approval_updated"):
                recipients = recipients.filter(Q(is_staff=True) | Q(is_superuser=True) | Q(groups__name=settings.GROUP_MANAGER)).distinct()
            else:
                recipients = recipients.filter(pk=instance.requested_by_id)
        for recipient in recipients:
            item, _ = Notification.objects.get_or_create(
                recipient=recipient, company=company, event_key=event_key,
                defaults={"kind": kind, "object_id": instance.pk},
            )
            PushOutbox.objects.get_or_create(notification=item)


def visible_inbox(user, company):
    """Recheck current object access, even after reassignment/move/delete/revocation."""
    tasks = Task.objects.filter(company=company)
    if not is_manager(user):
        tasks = tasks.filter(Q(assigned_to=user) | Q(created_by=user))
    notices = Notice.objects.filter(Q(company=company) | Q(company__isnull=True))
    approvals = ApprovalRequest.objects.filter(company=company)
    if not is_manager(user):
        approvals = approvals.filter(requested_by=user)
    return Notification.objects.filter(recipient=user, company=company).filter(
        Q(kind__in=["task_assigned", "task_updated"], object_id__in=tasks.values("pk"))
        | Q(kind__in=["notice_published", "notice_updated"], object_id__in=notices.values("pk"))
        | Q(kind__in=APPROVAL_KINDS, object_id__in=approvals.values("pk"))
    )


def push_envelope(item):
    """Provider-neutral, privacy-safe draft. Not an APNs/FCM send implementation."""
    return {
        "title": "CAVI TEST",
        "body": "Có cập nhật công việc. Mở CAVI để xem chi tiết.",
        "data": {"notification_id": str(item.public_id), "channel": "preview"},
    }
