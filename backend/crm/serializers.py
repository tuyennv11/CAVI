from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ContactLog, Order, OrderItem, Partner, TierUpgradeRequest

User = get_user_model()


class AssignedToSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class ContactLogSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ContactLog
        fields = [
            "id",
            "customer",
            "contact_person",
            "outcome",
            "note",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class PartnerSerializer(serializers.ModelSerializer):
    assigned_to_detail = AssignedToSerializer(source="assigned_to", read_only=True)
    contact_count = serializers.IntegerField(source="contact_logs.count", read_only=True)
    order_count = serializers.IntegerField(source="orders.count", read_only=True)
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    debt = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_revenue = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    tenure_months = serializers.IntegerField(read_only=True)
    tier = serializers.ChoiceField(choices=Partner.Tier.choices, read_only=True)
    tier_source = serializers.ChoiceField(choices=["auto", "approved"], read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "contact_person",
            "phone",
            "note",
            "partner_type",
            "tier",
            "tier_source",
            "tenure_months",
            "total_revenue",
            "credit_limit",
            "debt",
            "assigned_to",
            "assigned_to_detail",
            "contact_count",
            "order_count",
            "created_at",
        ]


class TierUpgradeRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True)
    partner_name = serializers.CharField(source="partner.name", read_only=True)

    class Meta:
        model = TierUpgradeRequest
        fields = [
            "id",
            "partner",
            "partner_name",
            "requested_tier",
            "reason",
            "requested_by",
            "requested_by_name",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = ["requested_by", "status", "reviewed_by", "reviewed_at", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "description", "quantity", "unit_price", "unit_cost", "line_total", "line_profit"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "status",
            "note",
            "paid",
            "on_platform",
            "items",
            "total",
            "gross_profit",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        OrderItem.objects.bulk_create(OrderItem(order=order, **item) for item in items_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            OrderItem.objects.bulk_create(OrderItem(order=instance, **item) for item in items_data)
        return instance
