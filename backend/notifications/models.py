import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Private inbox. No copied business text, salary, customer name or device token."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    event_key = models.CharField(max_length=64)
    kind = models.CharField(max_length=30, choices=[
        ("task_assigned", "Được giao công việc"),
        ("task_updated", "Công việc thay đổi"),
        ("notice_published", "Thông báo nội bộ mới"),
        ("notice_updated", "Thông báo nội bộ thay đổi"),
        ("approval_submitted", "Yêu cầu mới cần duyệt"),
        ("approval_updated", "Nội dung trình duyệt thay đổi"),
        ("approval_approved", "Yêu cầu được duyệt"),
        ("approval_rejected", "Yêu cầu bị từ chối"),
        ("approval_paid", "Yêu cầu được đánh dấu đã chi"),
    ])
    object_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["recipient", "company", "event_key"], name="notification_once_per_user")]
        indexes = [models.Index(fields=["recipient", "company", "read_at", "id"], name="notification_inbox_idx")]


class PushOutbox(models.Model):
    """Durable intent only. No sender/provider configured; never claim delivery."""

    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name="push_intent")
    state = models.CharField(max_length=30, default="not_configured", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
