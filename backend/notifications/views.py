from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from companies.utils import get_active_company
from accounts.roles import is_manager
from approvals.models import ApprovalRequest
from crm.models import Notice, Task

from .service import visible_inbox

TEXT = {
    "task_assigned": ("Bạn có công việc được giao", "Mở để xem nội dung, người phụ trách và thời hạn."),
    "task_updated": ("Công việc có thay đổi", "Kiểm tra trạng thái, nội dung hoặc thời hạn mới."),
    "notice_published": ("Có thông báo nội bộ mới", "Đọc nội dung và hướng dẫn áp dụng trong công ty."),
    "notice_updated": ("Thông báo nội bộ được cập nhật", "Mở lại để xem nội dung hiện tại."),
    "approval_submitted": ("Có yêu cầu mới cần duyệt", "Mở nội dung và kiểm tra căn cứ trước khi quyết định."),
    "approval_updated": ("Nội dung trình duyệt đã thay đổi", "Xem lại nội dung hiện tại trước khi duyệt."),
    "approval_approved": ("Yêu cầu của bạn đã được duyệt", "Mở để xem kết quả và bước tiếp theo; chưa đồng nghĩa đã chi tiền."),
    "approval_rejected": ("Yêu cầu của bạn bị từ chối", "Mở để xem trạng thái hiện tại và trao đổi với người duyệt."),
    "approval_paid": ("Yêu cầu được đánh dấu đã chi", "Đây là trạng thái ghi nhận trong app, không phải xác nhận giao dịch ngân hàng."),
}


def serialize_item(item):
    title, body = TEXT[item.kind]
    return {"id": item.id, "kind": item.kind, "title": title, "body": body,
            "created_at": item.created_at, "read_at": item.read_at}


class PrivateInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False):
            raise NotFound()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    def inbox(self, request):
        return visible_inbox(request.user, get_active_company(request))


class InboxView(PrivateInboxView):
    def get(self, request):
        qs = self.inbox(request)
        unread_count = qs.filter(read_at__isnull=True).count()
        if request.query_params.get("unread") == "true":
            qs = qs.filter(read_at__isnull=True)
        before = request.query_params.get("before")
        if before:
            if not before.isascii() or not before.isdigit() or len(before) > 18:
                raise ValidationError("Mốc thông báo không hợp lệ.")
            qs = qs.filter(id__lt=int(before))
        rows = list(qs[:51])
        return Response({"results": [serialize_item(item) for item in rows[:50]],
                         "next_before": rows[49].id if len(rows) > 50 else None,
                         "unread_count": unread_count,
                         "push": {"enabled": False, "state": "not_configured"}})


class ReadInput(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=2**53-1), max_length=50, allow_empty=False)


class MarkReadView(PrivateInboxView):
    def post(self, request):
        form = ReadInput(data=request.data)
        form.is_valid(raise_exception=True)
        # Only the displayed IDs; a new arriving notification stays unread.
        changed = self.inbox(request).filter(id__in=form.validated_data["ids"], read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": changed})


class NotificationDetailView(PrivateInboxView):
    def get(self, request, pk):
        item = self.inbox(request).filter(pk=pk).first()
        if not item:
            raise NotFound("Thông báo không còn khả dụng hoặc bạn không có quyền xem.")
        data = serialize_item(item)
        if item.kind.startswith("task_"):
            source = Task.objects.filter(pk=item.object_id, company_id=item.company_id)
            if not is_manager(request.user):
                source = source.filter(Q(assigned_to=request.user) | Q(created_by=request.user))
            obj = source.first()
            if not obj:
                raise NotFound()
            data["detail"] = {"title": obj.title, "content": obj.content,
                              "status": obj.get_status_display(), "due_at": obj.due_at,
                              "destination": f"/records/task/{obj.pk}", "action_label": "Mở đúng công việc"}
        elif item.kind.startswith("approval_"):
            source = ApprovalRequest.objects.filter(pk=item.object_id, company_id=item.company_id)
            if not is_manager(request.user):
                source = source.filter(requested_by=request.user)
            obj = source.first()
            if not obj:
                raise NotFound()
            data["detail"] = {"title": obj.title, "content": obj.note, "status": obj.get_status_display(), "due_at": None,
                              "destination": f"/approvals?request={obj.pk}", "action_label": "Mở đúng yêu cầu ký duyệt"}
        else:
            obj = Notice.objects.filter(pk=item.object_id).filter(Q(company_id=item.company_id) | Q(company__isnull=True)).first()
            if not obj:
                raise NotFound()
            data["detail"] = {"title": obj.title, "content": obj.body,
                              "status": obj.code, "due_at": None,
                              "destination": f"/records/notice/{obj.pk}", "action_label": "Mở đúng thông báo nội bộ"}
        return Response(data)
