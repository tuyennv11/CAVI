from django.contrib import admin

from config.admin_utils import linked_fk
from ops.models import Shipment as OpsShipment

from .models import (
    Activity,
    KPITarget,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceInquiry,
    PriceInquiryMessage,
    PriceInquiryQuoteLine,
    PriceInquiryQuoteLineBid,
    PriceListItem,
    Quotation,
    QuotationLine,
    Task,
    TierUpgradeRequest,
)


class CustomerFieldMixin:
    """Field "customer" (Khách hàng) trên Order/Activity/PriceInquiry chỉ nên cho chọn Đối tác có
    is_customer=True — không thì 1 Đối tác chỉ đăng ký "Nhà cung cấp" (vd Chị Lụa) vẫn hiện ra khi
    tạo Đơn hàng/Hoạt động khách hàng/Hỏi giá mới, dù field này ghi rõ là "Khách hàng"."""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            kwargs["queryset"] = Partner.objects.filter(is_customer=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fk_name = "customer"
    fields = ("activity_type", "title", "status", "activity_at", "performed_by")
    readonly_fields = ("created_by", "created_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


# 3 inline dưới đây CHỈ ĐỌC (không cho thêm/sửa trực tiếp tại đây) — mục đích là để mở 1 Đối tác ra
# là THẤY NGAY toàn bộ Hỏi giá/Đơn hàng/Yêu cầu nâng hạng đã gắn với đối tác đó (trước đây các bảng
# này hoàn toàn tách rời, chỉ nối ngầm qua field "Khách hàng"/"Đối tác" nên không nhìn thấy được
# mối liên kết nếu không biết trước). "show_change_link" cho bấm thẳng vào 1 dòng để mở trang đầy
# đủ của Hỏi giá/Đơn hàng đó (sửa chi tiết, xem tin nhắn trao đổi... vẫn làm ở trang riêng, đủ chỗ
# hơn — trang Đối tác chỉ để xem tổng quan).
class PriceInquiryInline(admin.TabularInline):
    model = PriceInquiry
    fk_name = "customer"
    extra = 0
    fields = ("id", "status", "cost_price", "floor_price", "ceiling_price", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderInline(admin.TabularInline):
    model = Order
    fk_name = "customer"
    extra = 0
    fields = ("id", "status", "paid", "total", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class TierUpgradeRequestInline(admin.TabularInline):
    model = TierUpgradeRequest
    extra = 0
    fields = ("requested_tier", "status", "requested_by", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ShipmentInline(admin.TabularInline):
    model = OpsShipment
    fk_name = "partner"
    extra = 0
    fields = ("id", "description", "tracking_code", "vh_status", "kt_status", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    # Mỗi Đối tác chỉ có 1 dòng — hiện hết field trên bảng danh sách (kéo ngang xem), chỉ Hoạt động/
    # Yêu cầu nâng hạng/Đơn hàng/Hỏi giá (1 đối tác có NHIỀU dòng) mới tách bảng riêng theo mã đối tác.
    list_display = (
        "name", "is_customer", "is_supplier", "tier", "tier_override", "contact_person", "phone",
        "address", "note", "assigned_to", "created_at",
    )
    list_filter = ("is_customer", "is_supplier", "companies", "assigned_to")
    search_fields = ("name", "contact_person", "phone")
    filter_horizontal = ("companies",)
    inlines = [PriceInquiryInline, OrderInline, ShipmentInline, TierUpgradeRequestInline, ActivityInline]


@admin.register(Order)
class OrderAdmin(CustomerFieldMixin, admin.ModelAdmin):
    list_display = (
        "id", "customer_link", "status", "created_by", "source_quotation_link", "received_by", "received_at",
        "confirmed_by", "confirmed_at", "description", "note", "paid", "on_platform",
        "pickup_point", "pickup_ward", "delivery_point", "delivery_ward", "weight_kg", "cod_amount",
        "floor_pct", "ceiling_pct", "floor_price", "ceiling_price", "total", "gross_profit",
        "created_at", "updated_at",
    )
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]
    autocomplete_fields = ["pickup_ward", "delivery_ward"]

    @admin.display(description="Khách hàng")
    def customer_link(self, obj):
        return linked_fk(obj.customer)

    @admin.display(description="Báo giá gốc")
    def source_quotation_link(self, obj):
        return linked_fk(obj.source_quotation)


@admin.register(TierUpgradeRequest)
class TierUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "partner_link", "requested_tier", "reason", "status", "requested_by", "reviewed_by",
        "reviewed_at", "created_at",
    )
    list_filter = ("status", "requested_tier")

    @admin.display(description="Đối tác")
    def partner_link(self, obj):
        return linked_fk(obj.partner)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "body", "created_by", "created_at")


@admin.register(Activity)
class ActivityAdmin(CustomerFieldMixin, admin.ModelAdmin):
    # Bỏ cột "Tiêu đề" — trùng lặp với "Nội dung" (ActivitySerializer.create() tự suy tiêu đề từ
    # content khi bỏ trống, xem crm/serializers.py), giữ 1 cột đại diện đủ dùng, đỡ rối.
    list_display = (
        "customer_link", "activity_type", "status", "activity_at", "performed_by", "assigned_to",
        "contact_person", "content", "result", "note", "follow_up_date",
        "follow_up_time", "follow_up_done", "related_order", "related_reference", "created_by",
        "created_at", "updated_at",
    )
    list_filter = ("activity_type", "status")
    search_fields = ("title", "content")

    @admin.display(description="Khách hàng")
    def customer_link(self, obj):
        return linked_fk(obj.customer)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title", "content", "assigned_to", "created_by", "partner_link", "related_activity",
        "priority", "status", "due_at", "created_at", "updated_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "content")

    @admin.display(description="Khách hàng/đối tác liên quan")
    def partner_link(self, obj):
        return linked_fk(obj.partner)


@admin.register(KPITarget)
class KPITargetAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "revenue_target", "new_customer_target", "quote_target", "order_target", "task_target")
    list_filter = ("year", "month")


class PriceInquiryMessageInline(admin.TabularInline):
    model = PriceInquiryMessage
    extra = 0
    readonly_fields = ("author", "created_at")


class PriceInquiryQuoteLineInline(admin.TabularInline):
    model = PriceInquiryQuoteLine
    extra = 0
    readonly_fields = ("created_by", "created_at")


@admin.register(PriceInquiry)
class PriceInquiryAdmin(CustomerFieldMixin, admin.ModelAdmin):
    list_display = (
        "id", "customer_link", "status", "description", "cost_price", "floor_price", "ceiling_price",
        "floor_pct", "ceiling_pct", "quoted_by", "quoted_at", "created_by", "created_at", "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("customer__name",)
    inlines = [PriceInquiryQuoteLineInline, PriceInquiryMessageInline]

    @admin.display(description="Khách hàng")
    def customer_link(self, obj):
        return linked_fk(obj.customer)


# Đăng ký riêng (không chỉ để inline trong Hỏi giá) để Báo giá cạnh tranh bên dưới autocomplete được
# tới đúng dòng, và để bấm xem "Báo giá thắng" (winning_bid) round-trip qua lại được.
@admin.register(PriceInquiryQuoteLine)
class PriceInquiryQuoteLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "inquiry_link", "item_name", "quantity", "unit", "unit_cost", "winning_bid",
        "note", "created_by", "created_at",
    )
    search_fields = ("item_name",)
    autocomplete_fields = ["inquiry", "item"]

    @admin.display(description="Hỏi giá")
    def inquiry_link(self, obj):
        return linked_fk(obj.inquiry)


@admin.register(PriceInquiryQuoteLineBid)
class PriceInquiryQuoteLineBidAdmin(admin.ModelAdmin):
    list_display = ("id", "quote_line_link", "bidder", "unit_cost", "note", "created_at")
    search_fields = ("quote_line__item_name",)
    autocomplete_fields = ["quote_line"]

    @admin.display(description="Dòng dịch vụ cấu thành")
    def quote_line_link(self, obj):
        return linked_fk(obj.quote_line)


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "inquiry_link", "note", "pending_approval", "saved_at", "created_by",
        "created_at", "updated_at",
    )
    inlines = [QuotationLineInline]

    @admin.display(description="Hỏi giá")
    def inquiry_link(self, obj):
        return linked_fk(obj.inquiry)


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "category", "group_code", "group_name", "name", "unit", "floor_pct", "ceiling_pct", "is_active")
    list_filter = ("category", "group_code", "is_active")
    search_fields = ("item_code", "name", "group_name")
    list_editable = ("floor_pct", "ceiling_pct", "is_active")
