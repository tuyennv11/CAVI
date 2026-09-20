from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import OrderCost, OrderDocument, OrderFinance, OrderPayment


class OrderCostInline(admin.TabularInline):
    model = OrderCost
    extra = 0


class OrderPaymentInline(admin.TabularInline):
    model = OrderPayment
    extra = 0


class OrderDocumentInline(admin.TabularInline):
    model = OrderDocument
    extra = 0


class OrderFinanceResource(ExcelModelResource):
    class Meta:
        model = OrderFinance


class OrderCostResource(ExcelModelResource):
    class Meta:
        model = OrderCost


class OrderPaymentResource(ExcelModelResource):
    class Meta:
        model = OrderPayment


class OrderDocumentResource(ExcelModelResource):
    class Meta:
        model = OrderDocument
        exclude = ("file",)  # FileField — không xuất/nhập file qua Excel


@admin.register(OrderFinance)
class OrderFinanceAdmin(ImportExportModelAdmin):
    resource_classes = [OrderFinanceResource]
    list_display = ("order", "revenue_amount", "currency", "payment_due_at", "settlement_due_at", "settled_at")
    list_filter = ("currency", "contract_status", "deposit_required")
    search_fields = ("order__id", "order__customer__name")
    inlines = (OrderCostInline, OrderPaymentInline, OrderDocumentInline)


@admin.register(OrderCost)
class OrderCostAdmin(ImportExportModelAdmin):
    resource_classes = [OrderCostResource]


@admin.register(OrderPayment)
class OrderPaymentAdmin(ImportExportModelAdmin):
    resource_classes = [OrderPaymentResource]


@admin.register(OrderDocument)
class OrderDocumentAdmin(ImportExportModelAdmin):
    resource_classes = [OrderDocumentResource]
