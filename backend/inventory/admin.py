from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import Product, StockMovement, Warehouse


class WarehouseResource(ExcelModelResource):
    class Meta:
        model = Warehouse


class ProductResource(ExcelModelResource):
    class Meta:
        model = Product


class StockMovementResource(ExcelModelResource):
    class Meta:
        model = StockMovement


@admin.register(Warehouse)
class WarehouseAdmin(ImportExportModelAdmin):
    resource_classes = [WarehouseResource]
    # Bỏ "company" khỏi cột hiển thị + bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên giá trị luôn giống
    # nhau ở mọi dòng, không còn tác dụng lọc/phân biệt gì nữa (xem companies/admin.py).
    list_display = ("name", "address", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address")


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = [ProductResource]
    list_display = ("sku", "name", "unit", "cost_price", "sale_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("sku", "name")


@admin.register(StockMovement)
class StockMovementAdmin(ImportExportModelAdmin):
    resource_classes = [StockMovementResource]
    list_display = (
        "created_at", "movement_type", "product", "warehouse", "quantity", "unit_cost",
        "supplier", "created_by",
    )
    list_filter = ("movement_type", "warehouse")
    search_fields = ("product__sku", "product__name", "note")
    autocomplete_fields = ("product", "warehouse", "supplier")
