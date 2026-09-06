from datetime import timedelta

from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_manager

from .models import ContactLog, Order, Partner
from .permissions import IsManagerOrAssignedSales
from .serializers import ContactLogSerializer, OrderSerializer, PartnerSerializer

MONEY_FIELD = DecimalField(max_digits=16, decimal_places=2)


def _sum_revenue(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(F("items__quantity") * F("items__unit_price"), output_field=MONEY_FIELD), 0, output_field=MONEY_FIELD
        )
    )["total"]


def _sum_gross_profit(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(
                F("items__quantity") * (F("items__unit_price") - F("items__unit_cost")),
                output_field=MONEY_FIELD,
            ),
            0,
            output_field=MONEY_FIELD,
        )
    )["total"]


class PartnerViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    search_fields = ["name", "company", "phone", "email"]
    filterset_fields = ["assigned_to", "partner_type", "tier"]

    def get_queryset(self):
        qs = Partner.objects.select_related("assigned_to").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(assigned_to=self.request.user)

    def perform_create(self, serializer):
        # Nhân viên kinh doanh tạo đối tác mới thì mặc định tự phụ trách đối tác đó.
        if is_manager(self.request.user) and serializer.validated_data.get("assigned_to"):
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="contacts")
    def contacts(self, request, pk=None):
        partner = self.get_object()
        if request.method == "GET":
            logs = partner.contact_logs.select_related("created_by").all()
            return Response(ContactLogSerializer(logs, many=True).data)

        serializer = ContactLogSerializer(data={**request.data, "customer": partner.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=partner, created_by=request.user)
        return Response(serializer.data, status=201)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "customer", "paid", "on_platform"]

    def get_queryset(self):
        qs = Order.objects.select_related("customer", "created_by").prefetch_related("items").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(customer__assigned_to=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DashboardStatsView(APIView):
    """Số liệu tổng quan cho trang Dashboard — scope theo vai trò giống các ViewSet ở trên."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        partners = Partner.objects.all()
        orders = Order.objects.all()
        contacts = ContactLog.objects.select_related("customer", "created_by")
        if not is_manager(request.user):
            partners = partners.filter(assigned_to=request.user)
            orders = orders.filter(customer__assigned_to=request.user)
            contacts = contacts.filter(customer__assigned_to=request.user)

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = orders.filter(created_at__gte=month_start)

        recent_orders = orders.select_related("customer").order_by("-created_at")[:8]
        recent_contacts = contacts.order_by("-created_at")[:8]
        activity = sorted(
            [
                {
                    "type": "order",
                    "at": o.created_at,
                    "text": f"Đơn hàng #{o.id} cho {o.customer.name}",
                }
                for o in recent_orders
            ]
            + [
                {
                    "type": "contact",
                    "at": c.created_at,
                    "text": f"Chăm sóc {c.customer.name}: {c.note[:80]}",
                }
                for c in recent_contacts
            ],
            key=lambda item: item["at"],
            reverse=True,
        )[:8]

        return Response(
            {
                "total_customers": partners.count(),
                "new_customers_week": partners.filter(created_at__gte=week_ago).count(),
                "orders_this_month": orders_this_month.count(),
                "revenue_this_month": _sum_revenue(orders_this_month),
                "total_revenue_all_time": _sum_revenue(orders),
                "gross_profit_this_month": _sum_gross_profit(orders_this_month),
                "gross_profit_on_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=True)
                ),
                "gross_profit_off_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=False)
                ),
                "recent_activity": activity,
            }
        )
