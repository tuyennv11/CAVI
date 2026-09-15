from decimal import Decimal

from django.db import transaction
from datetime import timedelta

from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.roles import is_manager
from companies.mixins import CompanyScopedMixin
from rest_framework.exceptions import PermissionDenied

from .models import OrderCost, OrderDocument, OrderFinance, OrderPayment, next_monday_noon
from .permissions import IsFinanceStaff
from .serializers import (
    FinanceSummarySerializer,
    OrderCostSerializer,
    OrderDocumentSerializer,
    OrderFinanceSerializer,
    OrderPaymentSerializer,
)


class OrderFinanceViewSet(
    CompanyScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    serializer_class = OrderFinanceSerializer
    permission_classes = [IsFinanceStaff]
    company_field = "order__company"
    filterset_fields = ["order__status", "contract_status", "currency"]
    search_fields = ["order__customer__name", "order__id", "note"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return self.scope_by_company(
            OrderFinance.objects.select_related(
                "order", "order__company", "order__customer", "credit_approved_by", "revenue_recorded_by"
            ).prefetch_related("order__items", "costs", "payments", "documents")
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        records = list(self.get_queryset())
        data = {
            "revenue": sum((row.amount_to_vnd(row.effective_revenue) for row in records), start=Decimal("0")),
            "cost": sum((row.amount_to_vnd(row.total_cost) for row in records), start=Decimal("0")),
            "gross_profit": sum((row.amount_to_vnd(row.effective_revenue - row.total_cost) for row in records), start=Decimal("0")),
            "collected": sum((row.amount_to_vnd(row.collected_amount) for row in records), start=Decimal("0")),
            "debt": sum((row.amount_to_vnd(row.debt_amount) for row in records), start=Decimal("0")),
            "overdue_orders": sum(1 for row in records if row.overdue_days > 0),
            "unsettled_orders": sum(1 for row in records if row.completed_at and not row.settled_at),
        }
        return Response(FinanceSummarySerializer(data).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        obj = self.get_object()
        if obj.order.status == "cancelled":
            raise ValidationError("Không thể hoàn thành một đơn đã hủy.")
        completed_at = timezone.now()
        obj.completed_at = completed_at
        obj.settlement_due_at = next_monday_noon(completed_at)
        obj.payment_due_at = completed_at + timedelta(days=obj.credit_terms_days)
        obj.order.status = "done"
        obj.order.save(update_fields=["status"])
        obj.save(update_fields=["completed_at", "settlement_due_at", "payment_due_at", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="record-revenue")
    def record_revenue(self, request, pk=None):
        obj = self.get_object()
        obj.revenue_recorded_by = request.user
        obj.revenue_recorded_at = timezone.now()
        obj.save(update_fields=["revenue_recorded_by", "revenue_recorded_at", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="approve-credit")
    def approve_credit(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý có thẩm quyền duyệt công nợ.")
        obj = self.get_object()
        if obj.credit_terms_days == 0:
            raise ValidationError("Đơn này chưa khai báo số ngày công nợ.")
        obj.credit_approved_by = request.user
        obj.credit_approved_at = timezone.now()
        obj.save(update_fields=["credit_approved_by", "credit_approved_at", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        obj = self.get_object()
        if not obj.completed_at:
            raise ValidationError("Chỉ quyết toán sau khi đơn đã hoàn thành.")
        obj.settled_at = timezone.now()
        obj.save(update_fields=["settled_at", "updated_at"])
        return Response(self.get_serializer(obj).data)


class FinanceChildMixin(CompanyScopedMixin):
    permission_classes = [IsFinanceStaff]
    company_field = "finance__order__company"

    def get_finance(self, serializer):
        finance = serializer.validated_data.get("finance", serializer.instance.finance if serializer.instance else None)
        company = self.get_active_company()
        if finance.order.company_id != company.id:
            raise ValidationError("Đơn hàng không thuộc công ty đang thao tác.")
        supplier = serializer.validated_data.get("supplier", getattr(serializer.instance, "supplier", None))
        if supplier is not None and (not supplier.is_supplier or not supplier.companies.filter(pk=company.pk).exists()):
            raise ValidationError({"supplier": "Nhà cung cấp không thuộc công ty đang thao tác."})
        return finance

    def perform_update(self, serializer):
        self.get_finance(serializer)
        serializer.save()


class OrderCostViewSet(FinanceChildMixin, viewsets.ModelViewSet):
    serializer_class = OrderCostSerializer

    def get_queryset(self):
        return self.scope_by_company(OrderCost.objects.select_related("finance__order", "supplier", "created_by"))

    def perform_create(self, serializer):
        self.get_finance(serializer)
        serializer.save(created_by=self.request.user)


class OrderPaymentViewSet(FinanceChildMixin, viewsets.ModelViewSet):
    serializer_class = OrderPaymentSerializer

    def get_queryset(self):
        return self.scope_by_company(OrderPayment.objects.select_related("finance__order", "recorded_by"))

    def perform_create(self, serializer):
        finance = self.get_finance(serializer)
        with transaction.atomic():
            serializer.save(recorded_by=self.request.user)
            finance.order.paid = finance.debt_amount <= 0
            finance.order.save(update_fields=["paid"])

    def perform_destroy(self, instance):
        finance = instance.finance
        super().perform_destroy(instance)
        finance.order.paid = finance.debt_amount <= 0
        finance.order.save(update_fields=["paid"])


class OrderDocumentViewSet(FinanceChildMixin, viewsets.ModelViewSet):
    serializer_class = OrderDocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return self.scope_by_company(OrderDocument.objects.select_related("finance__order", "uploaded_by"))

    def perform_create(self, serializer):
        self.get_finance(serializer)
        serializer.save(uploaded_by=self.request.user)
