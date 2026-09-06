from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Shipment, ShipmentBatch
from .serializers import ShipmentBatchSerializer, ShipmentSerializer


class ShipmentViewSet(viewsets.ModelViewSet):
    """Vận hành cần nhìn xuyên suốt công ty nên không giới hạn theo người phụ trách như Partner."""

    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Shipment.objects.select_related("partner", "assigned_operator", "created_by").all()
    filterset_fields = ["kd_status", "cu_status", "vh_status", "kt_status", "partner", "batch"]
    search_fields = ["tracking_code", "description", "route"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ShipmentBatchViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentBatchSerializer
    permission_classes = [IsAuthenticated]
    queryset = ShipmentBatch.objects.select_related("operator").all()
