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
        return Response(ApprovalRequestSerializer(obj).data)

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
