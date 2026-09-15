from django.contrib import admin

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


@admin.register(OrderFinance)
class OrderFinanceAdmin(admin.ModelAdmin):
    list_display = ("order", "revenue_amount", "currency", "payment_due_at", "settlement_due_at", "settled_at")
    list_filter = ("currency", "contract_status", "deposit_required")
    search_fields = ("order__id", "order__customer__name")
    inlines = (OrderCostInline, OrderPaymentInline, OrderDocumentInline)


admin.site.register(OrderCost)
admin.site.register(OrderPayment)
admin.site.register(OrderDocument)
