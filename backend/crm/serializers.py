from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from approvals.models import ApprovalRequest

from .models import (
    Activity,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceInquiry,
    PriceInquiryMessage,
    PriceInquiryQuoteLine,
    PriceListItem,
    Quotation,
    QuotationLine,
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


class PriceListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceListItem
        fields = ["id", "category", "group_code", "group_name", "item_code", "name", "unit", "floor_pct", "ceiling_pct"]


class PriceInquiryQuoteLineSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    category = serializers.CharField(source="item.category", read_only=True, default=None)
    # Không bắt buộc ở đây — khi có chọn `item` thì create() tự điền lại từ bảng giá gốc bên dưới.
    item_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=50)
    floor_pct = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    ceiling_pct = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    line_cost = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_floor = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_ceiling = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = PriceInquiryQuoteLine
        fields = [
            "id",
            "inquiry",
            "item",
            "item_code",
            "category",
            "item_name",
            "unit",
            "floor_pct",
            "ceiling_pct",
            "quantity",
            "unit_cost",
            "note",
            "line_cost",
            "line_floor",
            "line_ceiling",
            "created_at",
        ]
        read_only_fields = ["inquiry", "created_at"]

    def validate(self, attrs):
        if not attrs.get("item") and not attrs.get("item_name"):
            raise serializers.ValidationError("Cần chọn dịch vụ từ bảng giá hoặc nhập tên dịch vụ.")
        item = attrs.get("item")
        inquiry = self.context.get("inquiry")
        if item and item.category == PriceListItem.Category.I and inquiry is not None:
            if inquiry.quote_lines.filter(item__category=PriceListItem.Category.I).exists():
                raise serializers.ValidationError("Một đơn hàng chỉ được chọn 1 dịch vụ thuộc nhóm I.")
        return attrs

    def create(self, validated_data):
        item = validated_data.get("item")
        if item:
            if not validated_data.get("item_name"):
                validated_data["item_name"] = item.name
            if not validated_data.get("unit"):
                validated_data["unit"] = item.unit
            validated_data["floor_pct"] = item.floor_pct
            validated_data["ceiling_pct"] = item.ceiling_pct
        return super().create(validated_data)


class QuotationLineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationLine
        fields = ["id", "item_name", "unit", "quantity", "price", "line_total"]


class QuotationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="inquiry.customer.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    lines = QuotationLineSerializer(many=True)
    total = serializers.SerializerMethodField()
    floor_price = serializers.DecimalField(
        source="inquiry.floor_price", max_digits=14, decimal_places=2, read_only=True
    )
    ceiling_price = serializers.DecimalField(
        source="inquiry.ceiling_price", max_digits=14, decimal_places=2, read_only=True
    )
    pending_approval_id = serializers.IntegerField(source="pending_approval.id", read_only=True, default=None)
    pending_approval_status = serializers.CharField(source="pending_approval.status", read_only=True, default=None)

    class Meta:
        model = Quotation
        fields = [
            "id",
            "inquiry",
            "customer_name",
            "note",
            "lines",
            "total",
            "floor_price",
            "ceiling_price",
            "pending_approval_id",
            "pending_approval_status",
            "pending_snapshot",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["inquiry", "created_by", "created_at", "updated_at", "pending_snapshot"]

    def get_total(self, obj):
        return sum((line.line_total for line in obj.lines.all()), Decimal("0"))

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        if lines_data is not None:
            total = sum((line["quantity"] * line["price"] for line in lines_data), Decimal("0"))
            inquiry = instance.inquiry
            floor = inquiry.floor_price if inquiry.floor_price is not None else Decimal("0")
            ceiling = inquiry.ceiling_price
            within_bounds = total >= floor and (ceiling is None or total <= ceiling)
            if not within_bounds:
                approval = instance.pending_approval
                if not (approval and approval.status == ApprovalRequest.Status.APPROVED):
                    raise serializers.ValidationError(
                        "Giá tổng báo giá phải nằm trong khoảng giá sàn - giá trần của phần dịch vụ cấu "
                        "thành đơn hàng. Gửi đề xuất để Cung ứng duyệt trước khi lưu."
                    )
            # Lưu thành công (trong khoảng, hoặc đề xuất ngoài khoảng đã được duyệt) — dọn sạch đề xuất
            # cũ, vì nội dung vừa lưu giờ đã là bản chính thức, không còn gì "đang chờ" nữa.
            instance.pending_approval = None
            instance.pending_snapshot = None
        instance.note = validated_data.get("note", instance.note)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            QuotationLine.objects.bulk_create(QuotationLine(quotation=instance, **line) for line in lines_data)
        return instance


class PriceInquirySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    quoted_by_name = serializers.CharField(source="quoted_by.username", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    messages = PriceInquiryMessageSerializer(many=True, read_only=True)
    quote_lines = PriceInquiryQuoteLineSerializer(many=True, read_only=True)
    quotation = QuotationSerializer(read_only=True, required=False)

    class Meta:
        model = PriceInquiry
        fields = [
            "id",
            "customer",
            "customer_name",
            "description",
            "image",
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
            "quote_lines",
            "quotation",
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
            "source_quotation",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "source_quotation"]

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
