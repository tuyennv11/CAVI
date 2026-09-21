from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import InventoryReservation, Lot, LotCost, Product, StockMovement, Warehouse


class WarehouseResource(ExcelModelResource):
    class Meta:
        model = Warehouse


class ProductResource(ExcelModelResource):
    class Meta:
        model = Product


class StockMovementResource(ExcelModelResource):
    class Meta:
        model = StockMovement


class LotResource(ExcelModelResource):
    class Meta:
        model = Lot


class InventoryReservationResource(ExcelModelResource):
    class Meta:
        model = InventoryReservation


@admin.register(Warehouse)
class WarehouseAdmin(ImportExportModelAdmin):
    resource_classes = [WarehouseResource]
    # Bỏ "company" khỏi cột hiển thị + bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên giá trị luôn giống
    # nhau ở mọi dòng, không còn tác dụng lọc/phân biệt gì nữa (xem companies/admin.py).
    list_display = ("name", "address", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address")
    # Field tự điền qua default=get_default_company_id (xem inventory/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = [ProductResource]
    list_display = ("sku", "name", "unit", "cost_price", "sale_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("sku", "name")
    exclude = ("company",)


@admin.register(StockMovement)
class StockMovementAdmin(ImportExportModelAdmin):
    resource_classes = [StockMovementResource]
    list_display = (
        "created_at", "movement_type", "product", "warehouse", "quantity", "unit_cost",
        "supplier", "lot", "created_by",
    )
    list_filter = ("movement_type", "warehouse")
    search_fields = ("product__sku", "product__name", "note")
    autocomplete_fields = ("product", "warehouse", "supplier", "lot")


class LotCostInline(admin.TabularInline):
    model = LotCost
    extra = 1
    readonly_fields = ("created_by", "created_at")


@admin.register(Lot)
class LotAdmin(ImportExportModelAdmin):
    resource_classes = [LotResource]
    list_display = (
        "code", "product", "supplier", "quantity", "unit_price", "origin_point", "warehouse",
        "shipped_at", "received_at", "total_cost", "unit_cost", "created_by", "created_at",
    )
    list_filter = ("warehouse",)
    search_fields = ("code", "product__sku", "product__name")
    readonly_fields = ("code",)
    autocomplete_fields = ("purchase_request_item", "product", "supplier", "warehouse")
    inlines = [LotCostInline]

    @admin.display(description="Tổng giá vốn")
    def total_cost(self, obj):
        return obj.total_cost

    @admin.display(description="Giá vốn/đơn vị")
    def unit_cost(self, obj):
        return obj.unit_cost


@admin.register(InventoryReservation)
class InventoryReservationAdmin(ImportExportModelAdmin):
    resource_classes = [InventoryReservationResource]
    list_display = (
        "product", "warehouse", "quantity", "price_request_item", "status", "created_by",
        "created_at", "released_at",
    )
    list_filter = ("status", "warehouse")
    search_fields = ("product__sku", "product__name")
    autocomplete_fields = ("product", "warehouse", "price_request_item")
