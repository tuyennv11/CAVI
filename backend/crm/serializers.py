from decimal import Decimal

from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.roles import is_manager
from approvals.models import ApprovalRequest
from companies.models import Company
from companies.utils import get_active_company
from hr.models import Profile

from .models import (
    Activity,
    CostQuote,
    CostQuoteItem,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceRequest,
    PriceRequestItem,
    PriceInquiryMessage,
    PriceInquiryQuoteLine,
    PriceInquiryQuoteLineBid,
    PriceListItem,
    PurchaseRequestItem,
    Quotation,
    QuotationLine,
    SupplierQuote,
    Task,
)
from .services.price_request import refresh_source_status

User = get_user_model()


class AssignedToSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class AssignedProfileSerializer(serializers.ModelSerializer):
    """Đối tác.assigned_to liên kết Hồ sơ nhân sự (không phải User) — khác AssignedToSerializer ở
    trên (dùng cho Activity/Task, vẫn liên kết User)."""

    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["id", "employee_code", "username", "full_name"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


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


class PriceInquiryQuoteLineBidSerializer(serializers.ModelSerializer):
    bidder_name = serializers.SerializerMethodField()

    class Meta:
        model = PriceInquiryQuoteLineBid
        fields = ["id", "quote_line", "bidder", "bidder_name", "unit_cost", "note", "created_at"]
        read_only_fields = ["bidder", "created_at"]

    def get_bidder_name(self, obj):
        if not obj.bidder:
            return None
        return obj.bidder.get_full_name() or obj.bidder.username

    def validate_quote_line(self, quote_line):
        # Sàn tự đóng khi Hỏi giá đã chốt giá — không cho chào giá thêm sau mốc đó, tránh chào giá
        # rồi âm thầm lệch với cost_price tổng đã lưu lúc confirm-quote.
        if quote_line.inquiry.status != PriceRequest.Status.CHO_CUNG_UNG:
            raise serializers.ValidationError("Hỏi giá này đã đóng, không thể chào giá thêm.")
        return quote_line


class PriceInquiryQuoteLineSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    category = serializers.CharField(source="item.category", read_only=True, default=None)
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    product_sku = serializers.CharField(source="product.sku", read_only=True, default=None)
    # Không bắt buộc ở đây — khi có chọn `item` thì create() tự điền lại từ bảng giá gốc bên dưới.
    item_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=50)
    floor_pct = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    ceiling_pct = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    line_cost = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_floor = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    line_ceiling = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    # 3 field dưới đây phục vụ Sàn báo giá cạnh tranh (xem crm/views.py PriceInquiryQuoteLineBidViewSet) —
    # sàn liệt kê dòng của MỌI Hỏi giá đang mở cùng lúc nên cần biết thuộc khách hàng/trạng thái nào
    # ngay trên dòng, không phải gọi thêm API để tra cứu.
    inquiry_status = serializers.CharField(source="inquiry.status", read_only=True)
    customer_id = serializers.IntegerField(source="inquiry.customer_id", read_only=True)
    customer_name = serializers.CharField(source="inquiry.customer.name", read_only=True)
    bids = PriceInquiryQuoteLineBidSerializer(many=True, read_only=True)

    class Meta:
        model = PriceInquiryQuoteLine
        fields = [
            "id",
            "inquiry",
            "inquiry_status",
            "customer_id",
            "customer_name",
            "item",
            "item_code",
            "category",
            "product",
            "product_name",
            "product_sku",
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
            "winning_bid",
            "bids",
            "created_at",
        ]
        read_only_fields = ["inquiry", "winning_bid", "created_at"]

    def validate(self, attrs):
        inquiry = self.context.get("inquiry") or getattr(self.instance, "inquiry", None)
        item = attrs.get("item")
        product = attrs.get("product")

        # Công ty Vận chuyển dùng "item" (dịch vụ), công ty Thương mại dùng "product" (hàng hoá) —
        # 2 khái niệm loại trừ nhau, tuỳ theo loại hình của công ty đang tạo Hỏi giá này.
        if inquiry is not None and inquiry.company.business_type == Company.BusinessType.TRADING:
            if not product:
                raise serializers.ValidationError("Công ty thương mại cần chọn hàng hoá.")
            if not attrs.get("item_name") and not product:
                raise serializers.ValidationError("Cần chọn hàng hoá.")
        else:
            if not item and not attrs.get("item_name"):
                raise serializers.ValidationError("Cần chọn dịch vụ từ bảng giá hoặc nhập tên dịch vụ.")
            if item and item.category == PriceListItem.Category.I and inquiry is not None:
                if inquiry.quote_lines.filter(item__category=PriceListItem.Category.I).exists():
                    raise serializers.ValidationError("Một đơn hàng chỉ được chọn 1 dịch vụ thuộc nhóm I.")
        return attrs

    def create(self, validated_data):
        item = validated_data.get("item")
        product = validated_data.get("product")
        if item:
            if not validated_data.get("item_name"):
                validated_data["item_name"] = item.name
            if not validated_data.get("unit"):
                validated_data["unit"] = item.unit
            validated_data["floor_pct"] = item.floor_pct
            validated_data["ceiling_pct"] = item.ceiling_pct
        elif product:
            if not validated_data.get("item_name"):
                validated_data["item_name"] = product.name
            if not validated_data.get("unit"):
                validated_data["unit"] = product.unit
            if not validated_data.get("unit_cost"):
                validated_data["unit_cost"] = product.cost_price
        return super().create(validated_data)


class QuotationLineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationLine
        fields = ["id", "product", "item_name", "unit", "quantity", "price", "line_total"]


class QuotationSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="inquiry.customer_id", read_only=True)
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
            "customer_id",
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
            "saved_at",
        ]
        read_only_fields = ["inquiry", "created_by", "created_at", "updated_at", "pending_approval", "pending_snapshot", "saved_at"]

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
        if "saved_at" in validated_data:
            instance.saved_at = validated_data["saved_at"]
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            QuotationLine.objects.bulk_create(QuotationLine(quotation=instance, **line) for line in lines_data)
        return instance


class CostQuoteItemSerializer(serializers.ModelSerializer):
    # 3 field dưới đây là property tính tự động trên model (không lưu DB) — luôn read-only, không
    # cho gửi lên khi tạo/sửa (xem CostQuoteItem.total_cost/total_volume_m3/total_weight_kg).
    total_cost = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True, allow_null=True)
    total_volume_m3 = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True, allow_null=True)
    total_weight_kg = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = CostQuoteItem
        fields = [
            "id", "item_name", "quantity", "unit", "unit_cost",
            "unit_length_cm", "unit_width_cm", "unit_height_cm", "unit_weight_kg",
            "total_cost", "total_volume_m3", "total_weight_kg",
        ]


from .market_serializers import FreightOfferSerializer, SourcingPlanSerializer
from .services.sourcing import comparison_key, goods_total, live, readiness, freight_total


class CostQuoteSerializer(serializers.ModelSerializer):
    freight_offers = FreightOfferSerializer(many=True, read_only=True)
    market = serializers.SerializerMethodField()

    def get_market(self, obj):
        total = goods_total(obj)
        shipping = freight_total(obj, obj.shipping_rate, obj.shipping_rate_basis)
        return {"goods_total": str(total) if total is not None else None,
                "shipping_total": str(shipping) if shipping is not None else None,
                "comparison_key": comparison_key(obj), "is_live": live(obj),
                "issues": readiness(obj)}

    def validate(self, data):
        rows = data.get("items", [])
        if not rows:
            raise serializers.ValidationError({"items": "Cần ít nhất một mặt hàng."})
        for row in rows:
            if not row.get("item_name", "").strip() or not row.get("unit", "").strip() or not row.get("quantity") or row["quantity"] <= 0:
                raise serializers.ValidationError({"items": "Nhập tên hàng, số lượng dương và ĐVT cho mọi dòng."})
            for field in ["unit_cost", "unit_length_cm", "unit_width_cm", "unit_height_cm", "unit_weight_kg"]:
                if row.get(field) is not None and row[field] < 0:
                    raise serializers.ValidationError({"items": "Giá và quy cách không được âm."})
        if data.get("shipping_rate") is not None and data["shipping_rate"] < 0:
            raise serializers.ValidationError({"shipping_rate": "Cước không được âm."})
        if data.get("confirmed") and (not data.get("supplier_name", "").strip() or not data.get("valid_until")):
            raise serializers.ValidationError("Giá xác nhận cần tên NCC và hạn hiệu lực.")
        return data

    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)
    province_name = serializers.CharField(source="province.name", read_only=True, default=None)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)
    items = CostQuoteItemSerializer(many=True)
    # shipping_cost là property tính tự động (Giá cước × tổng trọng lượng/thể tích mọi mặt hàng),
    # không cho gửi lên — xem CostQuote.shipping_cost/shipping_rate/shipping_rate_basis.
    shipping_cost = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = CostQuote
        fields = [
            "id", "price_request_item", "country", "country_name", "province", "province_name",
            "district", "district_name", "ward", "ward_name", "street_address",
            "shipping_rate", "shipping_rate_basis", "shipping_cost",
            "note", "items", "created_by", "created_by_name", "created_at", "updated_at",
            "supplier_name", "carrier_name", "confirmed", "valid_until", "available_at", "tax_basis",
            "payment_terms", "delivery_terms", "delivery_snapshot", "active", "supersedes", "freight_offers", "market",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "delivery_snapshot", "active"]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        cost_quote = CostQuote.objects.create(**validated_data)
        CostQuoteItem.objects.bulk_create(CostQuoteItem(cost_quote=cost_quote, **item) for item in items_data)
        return cost_quote

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            CostQuoteItem.objects.bulk_create(CostQuoteItem(cost_quote=instance, **item) for item in items_data)
        return instance


class PriceRequestItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    purchase_request_item_id = serializers.SerializerMethodField()
    price_request_code = serializers.CharField(source="price_request.code", read_only=True, default=None)
    customer_name = serializers.CharField(source="price_request.customer.name", read_only=True, default=None)
    assigned_to_id = serializers.IntegerField(source="price_request.assigned_to_id", read_only=True, default=None)
    assigned_to_name = serializers.SerializerMethodField()
    cost_quotes = CostQuoteSerializer(many=True, read_only=True)
    sourcing_plans = SourcingPlanSerializer(many=True, read_only=True)
    # Địa chỉ giao hàng cho KHÁCH đã nhập sẵn trên Yêu cầu giá gốc (Sales hỏi lúc tạo) — chỉ để tab
    # Trả lời yêu cầu giá hiện tham khảo, KHÔNG phải "Điểm nhận hàng" của CostQuote (đó là nơi NCC
    # giao tới, Cung ứng tự nhập riêng, 2 địa điểm khác nhau — vd khách ở Campuchia nhưng NCC giao
    # hàng về 1 kho ở Việt Nam trước).
    price_request_delivery_address = serializers.SerializerMethodField()

    class Meta:
        model = PriceRequestItem
        fields = [
            "id", "price_request", "price_request_code", "customer_name", "assigned_to_id", "assigned_to_name",
            "product", "product_name", "item_name", "image", "quantity", "unit", "source_status",
            "estimated_cost_price", "purchase_request_item_id", "cost_quotes", "price_request_delivery_address", "sourcing_plans",
        ]
        read_only_fields = ["source_status", "price_request"]

    def get_price_request_delivery_address(self, obj):
        pr = obj.price_request
        detail = ", ".join(filter(None, [pr.district.name if pr.district else None, pr.ward.name if pr.ward else None, pr.street_address]))
        return " · ".join(filter(None, [
            pr.country.name if pr.country else None,
            pr.province.name if pr.province else None,
            detail,
        ])) or None

    def get_purchase_request_item_id(self, obj):
        # Đã tạo Đề nghị mua từ dòng này chưa — frontend dựa vào đây để hiện nút "Tạo đề nghị mua"
        # hay link "Xem trên Sàn báo giá NCC" (xem PriceRequestItemViewSet.create_purchase_request).
        allocation = obj.purchase_allocations.first()
        return allocation.purchase_request_item_id if allocation else None

    def get_assigned_to_name(self, obj):
        assigned_to = obj.price_request.assigned_to
        return AssignedProfileSerializer(assigned_to).data["full_name"] if assigned_to else None


class SupplierQuoteSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    landed_unit_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = SupplierQuote
        fields = [
            "id", "purchase_request_item", "supplier", "supplier_name", "unit_price", "quantity", "unit",
            "pickup_point", "total_packages", "package_dimensions", "total_cbm", "total_weight_kg",
            "available_at", "payment_terms", "delivery_terms", "shipping_cost", "landed_unit_cost",
            "note", "is_selected", "selection_note", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["is_selected", "selection_note", "created_by", "created_at"]


class PurchaseRequestItemSerializer(serializers.ModelSerializer):
    """Dòng Đề nghị mua hiển thị trên Sàn báo giá NCC — kèm các Yêu cầu giá đang chờ dòng này (để
    biết ai được phép chọn báo giá thắng, xem SupplierQuoteViewSet.select) và mọi báo giá đã có."""

    purchase_request_code = serializers.CharField(source="purchase_request.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    price_requests = serializers.SerializerMethodField()
    supplier_quotes = SupplierQuoteSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseRequestItem
        fields = [
            "id", "purchase_request", "purchase_request_code", "product", "product_name", "item_name",
            "quantity", "unit", "price_requests", "supplier_quotes",
        ]

    def get_price_requests(self, obj):
        seen = {}
        for allocation in obj.allocations.select_related(
            "price_request_item__price_request__customer", "price_request_item__price_request__assigned_to"
        ):
            pri = allocation.price_request_item
            if pri is None:
                continue
            pr = pri.price_request
            if pr.id in seen:
                continue
            seen[pr.id] = {
                "id": pr.id,
                "code": pr.code,
                "customer_name": pr.customer.name,
                "assigned_to_id": pr.assigned_to_id,
                "assigned_to_name": AssignedProfileSerializer(pr.assigned_to).data["full_name"]
                if pr.assigned_to else None,
            }
        return list(seen.values())


class PriceRequestSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    assigned_to_detail = AssignedProfileSerializer(source="assigned_to", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)
    province_name = serializers.CharField(source="province.name", read_only=True, default=None)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)
    items = PriceRequestItemSerializer(many=True)
    messages = PriceInquiryMessageSerializer(many=True, read_only=True)
    quote_lines = PriceInquiryQuoteLineSerializer(many=True, read_only=True)
    quotations = QuotationSerializer(many=True, read_only=True)

    class Meta:
        model = PriceRequest
        fields = [
            "id",
            "code",
            "customer",
            "customer_name",
            "assigned_to",
            "assigned_to_detail",
            "items",
            "country",
            "country_name",
            "province",
            "province_name",
            "district",
            "district_name",
            "ward",
            "ward_name",
            "street_address",
            "description",
            "status",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "messages",
            "quote_lines",
            "quotations",
        ]
        read_only_fields = ["code", "status", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        price_request = PriceRequest.objects.create(**validated_data)
        for item_data in items_data:
            item = PriceRequestItem.objects.create(price_request=price_request, **item_data)
            refresh_source_status(item)
        return price_request

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                item = PriceRequestItem.objects.create(price_request=instance, **item_data)
                refresh_source_status(item)
        return instance


class PartnerSerializer(serializers.ModelSerializer):
    """Đối tác dùng 1 hồ sơ chung cho mọi công ty, nhưng chỉ hiển thị/giao dịch được ở đúng những
    công ty đã tick (field `companies`) — 1 đối tác có thể thuộc 1 hoặc nhiều công ty cùng lúc."""

    assigned_to_detail = AssignedProfileSerializer(source="assigned_to", read_only=True)
    companies_detail = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()
    order_count = serializers.SerializerMethodField()

    def get_companies_detail(self, obj):
        return [{"id": c.id, "code": c.code, "name": c.name} for c in obj.companies.all()]

    def get_activity_count(self, obj):
        return obj.activities.filter(company=self.context.get("company")).count()

    def get_order_count(self, obj):
        return obj.orders.filter(company=self.context.get("company")).count()

    class Meta:
        model = Partner
        fields = [
            "id",
            "code",
            "name",
            "contact_person",
            "phone",
            "note",
            "is_customer",
            "is_supplier",
            "companies",
            "companies_detail",
            "tier_override",
            "assigned_to",
            "assigned_to_detail",
            "activity_count",
            "order_count",
            "address",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by"]

    def validate(self, attrs):
        is_customer = attrs.get("is_customer", getattr(self.instance, "is_customer", None))
        is_supplier = attrs.get("is_supplier", getattr(self.instance, "is_supplier", None))
        if is_customer is False and is_supplier is False:
            raise serializers.ValidationError("Phải chọn ít nhất 1 loại: Khách hàng hoặc Nhà cung cấp.")
        # Tạo mới bắt buộc tick ít nhất 1 công ty (không thì đối tác vừa tạo không ai thấy được ở
        # đâu cả); sửa mà không đụng tới field này (PATCH không gửi lên) thì bỏ qua, giữ nguyên cũ.
        if "companies" in attrs and not attrs["companies"]:
            raise serializers.ValidationError("Phải tick ít nhất 1 công ty.")
        if self.instance is None and not attrs.get("companies"):
            raise serializers.ValidationError("Phải tick ít nhất 1 công ty.")
        return attrs


class NoticeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Notice
        fields = ["id", "code", "title", "body", "created_by", "created_by_name", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.IntegerField(source="product_id", read_only=True, default=None)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "description", "quantity", "actual_quantity", "unit_price", "unit_cost",
            "line_total", "line_profit",
        ]
        # actual_quantity chỉ được ghi qua OrderViewSet.record_actual (Vận hành), không sửa tự do
        # qua form sửa phiếu thường.
        read_only_fields = ["actual_quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    received_by_name = serializers.CharField(source="received_by.username", read_only=True, default=None)
    confirmed_by_name = serializers.CharField(source="confirmed_by.username", read_only=True, default=None)
    pickup_ward_name = serializers.CharField(source="pickup_ward.name", read_only=True, default=None)
    delivery_ward_name = serializers.CharField(source="delivery_ward.name", read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "status",
            "description",
            "image",
            "note",
            "paid",
            "on_platform",
            "items",
            "total",
            "gross_profit",
            "pickup_point",
            "pickup_ward",
            "pickup_ward_name",
            "delivery_point",
            "delivery_ward",
            "delivery_ward_name",
            "weight_kg",
            "cod_amount",
            "floor_pct",
            "ceiling_pct",
            "floor_price",
            "ceiling_price",
            "source_quotation",
            "received_by",
            "received_by_name",
            "received_at",
            "confirmed_by",
            "confirmed_by_name",
            "confirmed_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "created_at",
            "updated_at",
            "source_quotation",
            "received_by",
            "received_at",
            "confirmed_by",
            "confirmed_at",
            "floor_pct",
            "ceiling_pct",
            "floor_price",
            "ceiling_price",
        ]

    def validate_customer(self, customer):
        # Queryset scoping protects reads of existing orders, but does not stop
        # a crafted POST/PATCH from referencing another employee's customer.
        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError("Thiếu ngữ cảnh người dùng và công ty để xác minh khách hàng.")
        company = get_active_company(request)
        if not customer.is_customer or not customer.companies.filter(pk=company.pk).exists():
            raise serializers.ValidationError("Khách hàng không thuộc công ty đang thao tác.")
        if not is_manager(request.user) and customer.assigned_to_id != request.user.profile.id:
            raise serializers.ValidationError("Bạn chỉ được lập hoặc đổi đơn cho khách hàng mình phụ trách.")
        return customer

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
