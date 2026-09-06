from rest_framework import serializers

from .models import Shipment, ShipmentBatch


class ShipmentSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    assigned_operator_name = serializers.CharField(source="assigned_operator.username", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "partner",
            "partner_name",
            "description",
            "route",
            "tracking_code",
            "kd_status",
            "cu_status",
            "vh_status",
            "kt_status",
            "currency",
            "amount",
            "assigned_operator",
            "assigned_operator_name",
            "batch",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class ShipmentBatchSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.username", read_only=True)
    shipment_count = serializers.IntegerField(source="shipments.count", read_only=True)

    class Meta:
        model = ShipmentBatch
        fields = ["id", "route", "status", "operator", "operator_name", "shipment_count", "created_at"]
