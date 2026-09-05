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

from .models import ContactLog, Customer, Order
from .permissions import IsManagerOrAssignedSales
from .serializers import ContactLogSerializer, CustomerSerializer, OrderSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    search_fields = ["name", "company", "phone", "email"]
    filterset_fields = ["assigned_to"]

    def get_queryset(self):
        qs = Customer.objects.select_related("assigned_to").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(assigned_to=self.request.user)

    def perform_create(self, serializer):
        # Nhân viên kinh doanh tạo khách mới thì mặc định tự phụ trách khách đó.
        if is_manager(self.request.user) and serializer.validated_data.get("assigned_to"):
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="contacts")
    def contacts(self, request, pk=None):
        customer = self.get_object()
        if request.method == "GET":
            logs = customer.contact_logs.select_related("created_by").all()
            return Response(ContactLogSerializer(logs, many=True).data)

        serializer = ContactLogSerializer(data={**request.data, "customer": customer.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=customer, created_by=request.user)
        return Response(serializer.data, status=201)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "customer"]

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
        customers = Customer.objects.all()
        orders = Order.objects.all()
        contacts = ContactLog.objects.select_related("customer", "created_by")
        if not is_manager(request.user):
            customers = customers.filter(assigned_to=request.user)
            orders = orders.filter(customer__assigned_to=request.user)
            contacts = contacts.filter(customer__assigned_to=request.user)

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = orders.filter(created_at__gte=month_start)

        revenue = orders_this_month.aggregate(
            total=Coalesce(
                Sum(
                    F("items__quantity") * F("items__unit_price"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                ),
                0,
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )["total"]

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
                "total_customers": customers.count(),
                "new_customers_week": customers.filter(created_at__gte=week_ago).count(),
                "orders_this_month": orders_this_month.count(),
                "revenue_this_month": revenue,
                "recent_activity": activity,
            }
        )
