from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import is_manager

from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["request_type", "status"]

    def get_queryset(self):
        qs = ApprovalRequest.objects.select_related("requested_by", "reviewed_by").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(requested_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới duyệt được yêu cầu.")
        obj = self.get_object()
        obj.status = ApprovalRequest.Status.APPROVED
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save()
        # Đề xuất báo giá ngoài giá sàn/trần: duyệt xong áp dụng luôn nội dung đã gửi kèm đề xuất —
        # không bắt Kinh doanh phải quay lại bấm Lưu báo giá thêm 1 lần nữa cho cùng nội dung đó.
        if obj.request_type == ApprovalRequest.RequestType.PROPOSAL:
            self._apply_approved_quotation_proposal(obj)
        return Response(ApprovalRequestSerializer(obj).data)

    def _apply_approved_quotation_proposal(self, approval):
        from crm.models import Quotation, QuotationLine

        quotation = Quotation.objects.filter(pending_approval=approval).first()
        if quotation is None or not quotation.pending_snapshot:
            return
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
    def reject(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới từ chối được yêu cầu.")
        obj = self.get_object()
        obj.status = ApprovalRequest.Status.REJECTED
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save()
        return Response(ApprovalRequestSerializer(obj).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới đánh dấu đã chi.")
        obj = self.get_object()
        if obj.status != ApprovalRequest.Status.APPROVED:
            raise PermissionDenied("Chỉ đánh dấu đã chi cho yêu cầu đã duyệt.")
        obj.status = ApprovalRequest.Status.PAID
        obj.save()
        return Response(ApprovalRequestSerializer(obj).data)
