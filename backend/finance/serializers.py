from django.utils import timezone
from rest_framework import serializers

from .models import OrderCost, OrderDocument, OrderFinance, OrderPayment, next_monday_noon


class OrderCostSerializer(serializers.ModelSerializer):
    created_by = serializers.IntegerField(source="created_by_id", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    amount_in_record_currency = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = OrderCost
        fields = [
            "id", "finance", "category", "category_label", "supplier", "supplier_name",
            "description", "amount", "currency", "exchange_rate", "amount_in_record_currency",
            "incurred_at", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["created_at"]


class OrderPaymentSerializer(serializers.ModelSerializer):
    recorded_by = serializers.IntegerField(source="recorded_by_id", read_only=True, default=None)
    payment_type_label = serializers.CharField(source="get_payment_type_display", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.username", read_only=True, default=None)
    signed_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = OrderPayment
        fields = [
            "id", "finance", "payment_type", "payment_type_label", "amount", "currency",
            "exchange_rate", "signed_amount", "paid_at", "reference", "note",
            "recorded_by", "recorded_by_name", "created_at",
        ]
        read_only_fields = ["created_at"]


class OrderDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.IntegerField(source="uploaded_by_id", read_only=True, default=None)
    document_type_label = serializers.CharField(source="get_document_type_display", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", read_only=True, default=None)

    class Meta:
        model = OrderDocument
        fields = [
            "id", "finance", "document_type", "document_type_label", "title", "file",
            "document_number", "uploaded_by", "uploaded_by_name", "created_at",
        ]
        read_only_fields = ["created_at"]


class OrderFinanceSerializer(serializers.ModelSerializer):
    order_code = serializers.SerializerMethodField()
    customer_id = serializers.IntegerField(source="order.customer_id", read_only=True)
    customer_name = serializers.CharField(source="order.customer.name", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    order_created_at = serializers.DateTimeField(source="order.created_at", read_only=True)
    effective_revenue = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    base_cost = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    extra_cost = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_cost = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    gross_profit = serializers.SerializerMethodField()
    collected_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    recommended_deposit = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    debt_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overdue_days = serializers.IntegerField(read_only=True)
    overdue_bucket = serializers.CharField(read_only=True)
    credit_approval_level = serializers.CharField(read_only=True)
    contract_required_by_policy = serializers.BooleanField(read_only=True)
    costs = OrderCostSerializer(many=True, read_only=True)
    payments = OrderPaymentSerializer(many=True, read_only=True)
    documents = OrderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = OrderFinance
        fields = [
            "id", "order", "order_code", "customer_id", "customer_name", "order_status",
            "order_created_at", "currency", "revenue_amount", "effective_revenue", "cargo_value",
            "cargo_value_currency", "exchange_rate_to_vnd", "usd_exchange_rate_vnd", "deposit_required", "deposit_amount", "recommended_deposit",
            "credit_terms_days", "payment_due_at", "credit_approved_by", "credit_approved_at",
            "credit_approval_level", "contract_status", "contract_required_by_policy", "completed_at",
            "settlement_due_at", "settled_at", "revenue_recorded_by", "revenue_recorded_at",
            "base_cost", "extra_cost", "total_cost", "gross_profit", "collected_amount",
            "debt_amount", "overdue_days", "overdue_bucket", "note", "costs", "payments",
            "documents", "updated_at",
        ]
        read_only_fields = [
            "order", "payment_due_at", "credit_approved_by", "credit_approved_at", "completed_at",
            "settlement_due_at", "settled_at", "revenue_recorded_by", "revenue_recorded_at", "updated_at",
        ]

    def get_order_code(self, obj):
        return f"{obj.order.company.code}-{obj.order_id:06d}"

    def get_gross_profit(self, obj):
        return obj.effective_revenue - obj.total_cost

    def validate(self, attrs):
        cargo_value = attrs.get("cargo_value", getattr(self.instance, "cargo_value", 0))
        cargo_currency = attrs.get("cargo_value_currency", getattr(self.instance, "cargo_value_currency", "USD"))
        rate = attrs.get("exchange_rate_to_vnd", getattr(self.instance, "exchange_rate_to_vnd", 1))
        usd_rate = attrs.get("usd_exchange_rate_vnd", getattr(self.instance, "usd_exchange_rate_vnd", 25000))
        usd_value = cargo_value * rate / usd_rate if cargo_currency != OrderFinance.Currency.USD else cargo_value
        status = attrs.get("contract_status", getattr(self.instance, "contract_status", OrderFinance.ContractStatus.NONE))
        if usd_value >= 5000 and status == OrderFinance.ContractStatus.NONE:
            attrs["contract_status"] = OrderFinance.ContractStatus.REQUIRED
        return attrs


class FinanceSummarySerializer(serializers.Serializer):
    revenue = serializers.DecimalField(max_digits=20, decimal_places=2)
    cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=20, decimal_places=2)
    collected = serializers.DecimalField(max_digits=20, decimal_places=2)
    debt = serializers.DecimalField(max_digits=20, decimal_places=2)
    overdue_orders = serializers.IntegerField()
    unsettled_orders = serializers.IntegerField()
