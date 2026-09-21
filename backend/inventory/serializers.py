from rest_framework import serializers

from .models import Product, StockMovement, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "address", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    stock_on_hand = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "unit",
            "cost_price",
            "sale_price",
            "is_active",
            "stock_on_hand",
            "created_at",
        ]

    def get_stock_on_hand(self, obj):
        return obj.stock_on_hand()


class StockMovementSerializer(serializers.ModelSerializer):
    reference_order = serializers.IntegerField(source="reference_order_item.order_id", read_only=True, default=None)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "movement_type",
            "quantity",
            "unit_cost",
            "supplier",
            "supplier_name",
            "reference_order_item",
            "reference_order",
            "note",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["reference_order_item", "created_by", "created_at"]

    def validate(self, attrs):
        product = attrs.get("product") or getattr(self.instance, "product", None)
        warehouse = attrs.get("warehouse") or getattr(self.instance, "warehouse", None)
        movement_type = attrs.get("movement_type") or getattr(self.instance, "movement_type", None)
        quantity = attrs.get("quantity")
        company = self.context.get("company")

        if product and warehouse and product.company_id != warehouse.company_id:
            raise serializers.ValidationError("Hàng hoá và Kho phải cùng 1 công ty.")
        if company is not None and product is not None and product.company_id != company.id:
            raise serializers.ValidationError("Hàng hoá không thuộc công ty đang thao tác.")

        if quantity is not None:
            # quantity LUÔN dương ở mọi loại — chiều tăng/giảm suy hoàn toàn từ movement_type (xem
            # StockMovement.MovementType.decreasing_types()), kể cả Điều chỉnh tăng/giảm (trước đây
            # 1 loại "Điều chỉnh" duy nhất cho phép quantity âm, giờ đã tách 2 loại riêng).
            if quantity <= 0:
                raise serializers.ValidationError("Số lượng phải lớn hơn 0.")
        return attrs
