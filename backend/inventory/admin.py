from django.contrib import admin

from .models import Product, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "address", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "address")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "company", "unit", "cost_price", "sale_price", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("sku", "name")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "movement_type", "product", "warehouse", "quantity", "unit_cost",
        "supplier", "created_by",
    )
    list_filter = ("movement_type", "warehouse")
    search_fields = ("product__sku", "product__name", "note")
    autocomplete_fields = ("product", "warehouse", "supplier")
