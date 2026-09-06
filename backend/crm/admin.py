from django.contrib import admin

from .models import ContactLog, Order, OrderItem, Partner, TierUpgradeRequest


class ContactLogInline(admin.TabularInline):
    model = ContactLog
    extra = 0
    readonly_fields = ("created_by", "created_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "partner_type", "tier", "contact_person", "phone", "assigned_to", "created_at")
    list_filter = ("partner_type", "assigned_to")
    search_fields = ("name", "contact_person", "phone")
    inlines = [ContactLogInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "paid", "on_platform", "total", "gross_profit", "created_at")
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]


@admin.register(TierUpgradeRequest)
class TierUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ("partner", "requested_tier", "status", "requested_by", "reviewed_by", "created_at")
    list_filter = ("status", "requested_tier")
