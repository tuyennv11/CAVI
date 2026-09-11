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


# Đối tác luôn hiện đầu tiên trong mục CRM ở trang quản trị — mặc định Django sắp models theo thứ tự
# chữ cái của tên hiển thị, mà chữ "Đ" (mã Unicode riêng, không phải "D") lại xếp sau mọi chữ cái
# thường nên "Đối tác" tự rơi xuống cuối danh sách dù đây là bảng quan trọng/hay dùng nhất.
_original_get_app_list = admin.AdminSite.get_app_list


def _get_app_list_with_partner_first(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label=app_label)
    for app in app_list:
        if app["app_label"] == "crm":
            app["models"].sort(key=lambda m: 0 if m["object_name"] == "Partner" else 1)
    return app_list


admin.AdminSite.get_app_list = _get_app_list_with_partner_first
