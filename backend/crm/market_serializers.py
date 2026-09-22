from rest_framework import serializers
from .models import FreightOffer, SourcingPlan
from .services.sourcing import freight_total, live, readiness


class FreightOfferSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    total_cost = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()
    issues = serializers.SerializerMethodField()

    class Meta:
        model = FreightOffer
        fields = ["id", "goods_quote", "carrier_name", "rate", "basis", "confirmed", "valid_until",
                  "delivery_days", "tax_basis", "terms", "delivery_snapshot", "active", "supersedes",
                  "created_by", "created_by_name", "created_at", "total_cost", "is_live", "issues"]
        read_only_fields = ["active", "delivery_snapshot", "created_by", "created_at"]

    def get_total_cost(self, obj):
        value = freight_total(obj.goods_quote, obj.rate, obj.basis)
        return str(value) if value is not None else None

    def get_is_live(self, obj):
        return live(obj) and live(obj.goods_quote)

    def get_issues(self, obj):
        return readiness(obj.goods_quote, obj)

    def validate_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Cước không được âm.")
        return value


class SourcingPlanSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True, default=None)

    class Meta:
        model = SourcingPlan
        fields = "__all__"
        read_only_fields = ["status", "snapshot", "created_by", "reviewed_by", "created_at", "reviewed_at"]
