from django.contrib import admin

from .models import ContactLog, Customer, Order, OrderItem


class ContactLogInline(admin.TabularInline):
    model = ContactLog
    extra = 0
    readonly_fields = ("created_by", "created_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "phone", "assigned_to", "created_at")
    list_filter = ("assigned_to",)
    search_fields = ("name", "company", "phone", "email")
    inlines = [ContactLogInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]
