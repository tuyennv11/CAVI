from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import is_manager
from companies.mixins import CompanyScopedMixin
from config.notification_events import notification_snapshot, notify_change

from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer


class ApprovalRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["request_type", "status"]

    def get_queryset(self):
        qs = self.scope_by_company(
            ApprovalRequest.objects.select_related("requested_by", "reviewed_by").all()
        )
        if is_manager(self.request.user):
            return qs
        return qs.filter(requested_by=self.request.user)

    def locked_object(self):
        # Drop nullable joins before FOR UPDATE (PostgreSQL cannot lock their
        # nullable side). Keep the same tenant/role filtering as normal reads.
        obj = get_object_or_404(self.get_queryset().select_related(None).select_for_update(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @transaction.atomic
    def perform_create(self, serializer):
        obj = serializer.save(requested_by=self.request.user, company=self.get_active_company())
        notify_change("approval", obj, self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        from crm.models import Quotation

        obj = self.locked_object()
        if obj.status != ApprovalRequest.Status.PENDING:
            raise ValidationError("Yêu cầu đã có quyết định không được sửa nội dung; cần tạo yêu cầu mới để xem xét.")
        if Quotation.objects.filter(pending_approval=obj).exists():
            raise ValidationError("Đề xuất gắn với báo giá phải giữ đúng nội dung đã gửi, không sửa riêng tại Ký duyệt.")
        before = notification_snapshot(obj, "approval")
        serializer.instance = obj
        notify_change("approval", serializer.save(), self.request.user, before)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới duyệt được yêu cầu.")
        obj = self.locked_object()
        if obj.status == ApprovalRequest.Status.APPROVED:
            return Response(ApprovalRequestSerializer(obj).data)
        if obj.status != ApprovalRequest.Status.PENDING:
            raise ValidationError("Chỉ duyệt yêu cầu đang chờ; không ghi đè quyết định đã có.")
        before = notification_snapshot(obj, "approval")
        obj.status = ApprovalRequest.Status.APPROVED
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save()
        # Đề xuất báo giá ngoài giá sàn/trần: duyệt xong áp dụng luôn nội dung đã gửi kèm đề xuất —
        # không bắt Kinh doanh phải quay lại bấm Lưu báo giá thêm 1 lần nữa cho cùng nội dung đó.
        if obj.request_type == ApprovalRequest.RequestType.PROPOSAL:
            self._apply_approved_quotation_proposal(obj)
        notify_change("approval", obj, request.user, before)
        return Response(ApprovalRequestSerializer(obj).data)

    def _apply_approved_quotation_proposal(self, approval):
        from crm.models import Quotation, QuotationLine

        quotations = list(Quotation.objects.select_for_update().filter(pending_approval=approval)[:2])
        if not quotations:
            return
        if len(quotations) != 1:
            raise ValidationError("Đề xuất đang gắn nhiều báo giá; cần đối chiếu trước khi duyệt.")
        quotation = quotations[0]
        if quotation.inquiry.company_id != approval.company_id or not quotation.pending_snapshot:
            raise ValidationError("Báo giá khác công ty hoặc thiếu nội dung đề xuất; chưa thể duyệt.")
        snapshot = quotation.pending_snapshot
        quotation.note = snapshot.get("note", quotation.note)
        quotation.pending_approval = None
        quotation.pending_snapshot = None
        quotation.saved_at = timezone.now()
        quotation.save()
        quotation.lines.all().delete()
        QuotationLine.objects.bulk_create(
            QuotationLine(
                quotation=quotation,
                item_name=line.get("item_name", ""),
                unit=line.get("unit", ""),
                quantity=Decimal(str(line.get("quantity", 1))),
                price=Decimal(str(line.get("price", 0))),
            )
            for line in snapshot.get("lines", [])
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới từ chối được yêu cầu.")
        obj = self.locked_object()
        if obj.status == ApprovalRequest.Status.REJECTED:
            return Response(ApprovalRequestSerializer(obj).data)
        if obj.status != ApprovalRequest.Status.PENDING:
            raise ValidationError("Chỉ từ chối yêu cầu đang chờ; không ghi đè quyết định đã có.")
        before = notification_snapshot(obj, "approval")
        obj.status = ApprovalRequest.Status.REJECTED
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save()
        notify_change("approval", obj, request.user, before)
        return Response(ApprovalRequestSerializer(obj).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới đánh dấu đã chi.")
        obj = self.locked_object()
        if obj.request_type != ApprovalRequest.RequestType.SETTLEMENT:
            raise ValidationError("Chỉ yêu cầu quyết toán mới có bước đánh dấu đã chi.")
        if obj.status == ApprovalRequest.Status.PAID:
            return Response(ApprovalRequestSerializer(obj).data)
        if obj.status != ApprovalRequest.Status.APPROVED:
            raise PermissionDenied("Chỉ đánh dấu đã chi cho yêu cầu đã duyệt.")
        before = notification_snapshot(obj, "approval")
        obj.status = ApprovalRequest.Status.PAID
        obj.save()
        notify_change("approval", obj, request.user, before)
        return Response(ApprovalRequestSerializer(obj).data)
