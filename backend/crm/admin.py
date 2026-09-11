from django.contrib import admin
from django.utils.text import Truncator

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
    PriceListItem,
    Quotation,
    QuotationLine,
    Task,
    TierUpgradeRequest,
)


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fk_name = "customer"
    fields = ("activity_type", "title", "status", "activity_at", "performed_by")
    readonly_fields = ("created_by", "created_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    # Mỗi Đối tác chỉ có 1 dòng — hiện hết field trên bảng danh sách (kéo ngang xem), chỉ Hoạt động/
    # Yêu cầu nâng hạng/Đơn hàng/Hỏi giá (1 đối tác có NHIỀU dòng) mới tách bảng riêng theo mã đối tác.
    list_display = (
        "name", "partner_type", "tier", "tier_override", "contact_person", "phone",
        "province", "district", "ward", "street_address", "note_short", "assigned_to", "created_at",
    )
    list_filter = ("partner_type", "assigned_to")
    search_fields = ("name", "contact_person", "phone")
    inlines = [ActivityInline]
    autocomplete_fields = ["country", "province", "district", "ward"]

    @admin.display(description="Mô tả thêm")
    def note_short(self, obj):
        return Truncator(obj.note).chars(40)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "status", "created_by", "source_quotation", "received_by", "received_at",
        "confirmed_by", "confirmed_at", "description_short", "note", "paid", "on_platform",
        "pickup_point", "pickup_ward", "delivery_point", "delivery_ward", "weight_kg", "cod_amount",
        "floor_pct", "ceiling_pct", "floor_price", "ceiling_price", "total", "gross_profit",
        "created_at", "updated_at",
    )
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]
    autocomplete_fields = ["pickup_ward", "delivery_ward"]

    @admin.display(description="Mô tả lô hàng")
    def description_short(self, obj):
        return Truncator(obj.description).chars(40)


@admin.register(TierUpgradeRequest)
class TierUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "partner", "requested_tier", "reason_short", "status", "requested_by", "reviewed_by",
        "reviewed_at", "created_at",
    )
    list_filter = ("status", "requested_tier")

    @admin.display(description="Lý do")
    def reason_short(self, obj):
        return Truncator(obj.reason).chars(40)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "body_short", "created_by", "created_at")

    @admin.display(description="Nội dung")
    def body_short(self, obj):
        return Truncator(obj.body).chars(40)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "customer", "activity_type", "title", "status", "activity_at", "performed_by", "assigned_to",
        "contact_person", "content_short", "result_short", "note_short", "follow_up_date",
        "follow_up_time", "follow_up_done", "related_order", "related_reference", "created_by",
        "created_at", "updated_at",
    )
    list_filter = ("activity_type", "status")
    search_fields = ("title", "content")

    @admin.display(description="Nội dung")
    def content_short(self, obj):
        return Truncator(obj.content).chars(40)

    @admin.display(description="Kết quả")
    def result_short(self, obj):
        return Truncator(obj.result).chars(40)

    @admin.display(description="Ghi chú")
    def note_short(self, obj):
        return Truncator(obj.note).chars(40)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title", "content_short", "assigned_to", "created_by", "partner", "related_activity",
        "priority", "status", "due_at", "created_at", "updated_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "content")

    @admin.display(description="Nội dung")
    def content_short(self, obj):
        return Truncator(obj.content).chars(40)


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
class PriceInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "status", "description_short", "cost_price", "floor_price", "ceiling_price",
        "floor_pct", "ceiling_pct", "quoted_by", "quoted_at", "created_by", "created_at", "updated_at",
    )
    list_filter = ("status",)
    inlines = [PriceInquiryQuoteLineInline, PriceInquiryMessageInline]

    @admin.display(description="Mô tả")
    def description_short(self, obj):
        return Truncator(obj.description).chars(40)


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "inquiry", "note_short", "pending_approval", "saved_at", "created_by",
        "created_at", "updated_at",
    )
    inlines = [QuotationLineInline]

    @admin.display(description="Mô tả")
    def note_short(self, obj):
        return Truncator(obj.note).chars(40)


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "category", "group_code", "group_name", "name", "unit", "floor_pct", "ceiling_pct", "is_active")
    list_filter = ("category", "group_code", "is_active")
    search_fields = ("item_code", "name", "group_name")
    list_editable = ("floor_pct", "ceiling_pct", "is_active")
