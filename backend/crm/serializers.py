from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Activity,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceInquiry,
    PriceInquiryMessage,
    Task,
    TierUpgradeRequest,
)

User = get_user_model()


class AssignedToSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class ActivitySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source="performed_by.username", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    related_order_label = serializers.SerializerMethodField()
    # Không bắt nhập tiêu đề riêng — nội dung note đã đủ, tiêu đề tự suy ra ở create() nếu bỏ trống.
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = Activity
        fields = [
            "id",
            "customer",
            "customer_name",
            "activity_type",
            "title",
            "activity_at",
            "performed_by",
            "performed_by_name",
            "assigned_to",
            "assigned_to_name",
            "contact_person",
            "content",
            "result",
            "status",
            "follow_up_date",
            "follow_up_time",
            "follow_up_done",
            "note",
            "attachment",
            "related_order",
            "related_order_label",
            "related_reference",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def get_related_order_label(self, obj):
        return f"Đơn #{obj.related_order_id}" if obj.related_order_id else None

    def create(self, validated_data):
        if not validated_data.get("assigned_to"):
            validated_data["assigned_to"] = validated_data.get("performed_by")
        if "status" not in self.initial_data:
            is_historical = validated_data.get("activity_type") in Activity.HISTORICAL_TYPES
            validated_data["status"] = Activity.Status.DONE if is_historical else Activity.Status.NOT_PROCESSED
        if not validated_data.get("title"):
            content = (validated_data.get("content") or "").strip()
            validated_data["title"] = content[:60] if content else Activity(
                activity_type=validated_data.get("activity_type")
            ).get_activity_type_display()
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "content",
            "assigned_to",
            "assigned_to_name",
            "created_by",
            "created_by_name",
            "partner",
            "partner_name",
            "related_activity",
            "due_at",
            "priority",
            "status",
            "attachment",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        if not validated_data.get("assigned_to"):
            validated_data["assigned_to"] = self.context["request"].user
        return super().create(validated_data)


class PriceInquiryMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = PriceInquiryMessage
        fields = ["id", "inquiry", "author", "author_name", "content", "is_quote", "created_at"]
        read_only_fields = ["inquiry", "author", "is_quote", "created_at"]


class PriceInquirySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    quoted_by_name = serializers.CharField(source="quoted_by.username", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    messages = PriceInquiryMessageSerializer(many=True, read_only=True)

    class Meta:
        model = PriceInquiry
        fields = [
            "id",
            "customer",
            "customer_name",
            "description",
            "status",
            "cost_price",
            "floor_price",
            "ceiling_price",
            "quoted_by",
            "quoted_by_name",
            "quoted_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = [
            "status",
            "cost_price",
            "floor_price",
            "ceiling_price",
            "quoted_by",
            "quoted_at",
            "created_by",
            "created_at",
            "updated_at",
        ]


class PartnerSerializer(serializers.ModelSerializer):
    assigned_to_detail = AssignedToSerializer(source="assigned_to", read_only=True)
    activity_count = serializers.IntegerField(source="activities.count", read_only=True)
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
            "activity_count",
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


class NoticeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Notice
        fields = ["id", "code", "title", "body", "created_by", "created_by_name", "created_at"]
        read_only_fields = ["created_by", "created_at"]


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
