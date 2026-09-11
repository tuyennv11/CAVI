from django.contrib import admin

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
    list_display = ("name", "partner_type", "tier", "contact_person", "phone", "assigned_to", "created_at")
    list_filter = ("partner_type", "assigned_to")
    search_fields = ("name", "contact_person", "phone")
    inlines = [ActivityInline]
    autocomplete_fields = ["country", "province", "district", "ward"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "paid", "on_platform", "total", "gross_profit", "created_at")
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]
    autocomplete_fields = ["pickup_ward", "delivery_ward"]


@admin.register(TierUpgradeRequest)
class TierUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ("partner", "requested_tier", "status", "requested_by", "reviewed_by", "created_at")
    list_filter = ("status", "requested_tier")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "created_by", "created_at")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("customer", "activity_type", "title", "status", "activity_at", "performed_by", "follow_up_date")
    list_filter = ("activity_type", "status")
    search_fields = ("title", "content")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "created_by", "partner", "priority", "status", "due_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "content")


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
    list_display = ("id", "customer", "status", "cost_price", "floor_price", "ceiling_price", "quoted_by", "created_at")
    list_filter = ("status",)
    inlines = [PriceInquiryQuoteLineInline, PriceInquiryMessageInline]


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("id", "inquiry", "created_by", "created_at")
    inlines = [QuotationLineInline]


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "category", "group_code", "group_name", "name", "unit", "floor_pct", "ceiling_pct", "is_active")
    list_filter = ("category", "group_code", "is_active")
    search_fields = ("item_code", "name", "group_name")
    list_editable = ("floor_pct", "ceiling_pct", "is_active")
