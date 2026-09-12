from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from companies.mixins import CompanyScopedMixin

from .models import Shipment, ShipmentBatch
from .serializers import ShipmentBatchSerializer, ShipmentSerializer


class ShipmentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    """Vận hành cần nhìn xuyên suốt NGƯỜI PHỤ TRÁCH (không giới hạn theo assigned_operator như
    Partner giới hạn theo assigned_to) — nhưng vẫn phải lọc theo công ty đang thao tác, nếu không
    Vận hành của công ty này sẽ thấy luôn kiện hàng của công ty khác."""

    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["kd_status", "cu_status", "vh_status", "kt_status", "partner", "batch"]
    search_fields = ["tracking_code", "description", "route"]

    def get_queryset(self):
        return self.scope_by_company(
            Shipment.objects.select_related("partner", "assigned_operator", "created_by").all()
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_active_company())


class ShipmentBatchViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ShipmentBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.scope_by_company(ShipmentBatch.objects.select_related("operator").all())

    def perform_create(self, serializer):
        serializer.save(company=self.get_active_company())
