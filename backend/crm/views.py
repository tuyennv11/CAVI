from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
