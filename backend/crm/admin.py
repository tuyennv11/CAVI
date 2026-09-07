from django.contrib import admin

from .models import Activity, Notice, Order, OrderItem, Partner, TierUpgradeRequest


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


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "paid", "on_platform", "total", "gross_profit", "created_at")
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]


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
