from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from companies.mixins import CompanyScopedMixin

from .models import Product, StockMovement, Warehouse
from .serializers import ProductSerializer, StockMovementSerializer, WarehouseSerializer


class WarehouseViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.scope_by_company(Warehouse.objects.all())

    def perform_create(self, serializer):
        serializer.save(company=self.get_active_company())


class ProductViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["sku", "name"]

    def get_queryset(self):
        return self.scope_by_company(Product.objects.all())

    def perform_create(self, serializer):
        serializer.save(company=self.get_active_company())


class StockMovementViewSet(
    CompanyScopedMixin,
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """Nhật ký nhập/xuất kho. Không có Update/Destroy — mỗi dòng là 1 sự kiện đã xảy ra, sửa/xoá sẽ
    làm sai lệch lịch sử (giống ProfileChangeLog/CompensationRecord). Xuất kho (OUT) do bán hàng chỉ
    do hệ thống tự tạo lúc Kinh doanh xác nhận nhận hàng (OrderViewSet.confirm_received) — ở đây chỉ
    cho phép tạo Nhập kho (mua hàng chủ động, không phụ thuộc Hỏi giá) và Điều chỉnh (sau kiểm kê)."""

    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["product", "warehouse", "movement_type"]
    company_field = "product__company"

    def get_queryset(self):
        return self.scope_by_company(
            StockMovement.objects.select_related("product", "warehouse", "supplier", "created_by").all()
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self.get_active_company()
        return context

    def perform_create(self, serializer):
        if serializer.validated_data.get("movement_type") == StockMovement.MovementType.OUT:
            raise ValidationError(
                "Xuất kho do bán hàng được hệ thống tự tạo khi xác nhận nhận hàng, không tạo tay ở đây."
            )
        serializer.save(created_by=self.request.user)
