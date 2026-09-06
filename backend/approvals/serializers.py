from rest_framework import serializers

from .models import ApprovalRequest


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "request_type",
            "category",
            "title",
            "note",
            "amount",
            "currency",
            "requested_by",
            "requested_by_name",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = ["requested_by", "status", "reviewed_by", "reviewed_at", "created_at"]
