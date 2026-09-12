from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, DecimalField, F, Sum, When

from companies.models import Company


class Warehouse(models.Model):
    """Kho hàng — chỉ công ty Thương mại (LIVI, AVI...) dùng."""

    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.CASCADE, related_name="warehouses")
    name = models.CharField("Tên kho", max_length=255)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)  # text tự do, chỉ tham khảo
    is_active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kho hàng"
        verbose_name_plural = "Kho hàng"

    def __str__(self):
        return f"{self.name} ({self.company.code})"


class Product(models.Model):
    """Hàng hoá — mỗi công ty Thương mại có danh mục riêng."""

    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.CASCADE, related_name="products")
    sku = models.CharField("Mã hàng", max_length=50)
    name = models.CharField("Tên hàng hoá", max_length=255)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    # Chỉ mang tính tham khảo — giá vốn thật của từng lô nằm ở StockMovement (Nhập kho), giá vốn
    # trung bình dùng khi bán không tự tính ở đây, tính khi cần qua tổng hợp StockMovement.
    cost_price = models.DecimalField("Giá vốn tham khảo", max_digits=14, decimal_places=2, default=0)
    sale_price = models.DecimalField("Giá bán mặc định", max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField("Đang kinh doanh", default=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["sku"]
        unique_together = ["company", "sku"]
        verbose_name = "Hàng hoá"
        verbose_name_plural = "Hàng hoá"

    def __str__(self):
        return f"{self.sku} — {self.name}"

    def stock_on_hand(self, warehouse=None):
        """Tồn kho hiện tại — luôn tính trực tiếp từ StockMovement, không cache. Nhập/Điều chỉnh
        cộng, Xuất trừ (quantity của Điều chỉnh có thể âm — xem StockMovementSerializer.validate)."""
        qs = self.movements.all()
        if warehouse is not None:
            qs = qs.filter(warehouse=warehouse)
        agg = qs.aggregate(
            total=Sum(
                Case(
                    When(movement_type=StockMovement.MovementType.OUT, then=-F("quantity")),
                    default=F("quantity"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        return agg["total"] or Decimal("0")


class StockMovement(models.Model):
    """Nhật ký nhập/xuất kho — tồn kho LUÔN suy ra bằng cộng dồn bảng này (nhập trừ xuất), không lưu
    field "tồn kho hiện tại" riêng ở Product — đúng nguyên tắc history-as-rows đã dùng cho Lương/
    Nhật ký thay đổi trong hệ thống này, tránh lệch số liệu giữa 2 nơi lưu cùng 1 sự thật."""

    class MovementType(models.TextChoices):
        IN = "in", "Nhập kho"
        OUT = "out", "Xuất kho"
        ADJUSTMENT = "adjustment", "Điều chỉnh"

    product = models.ForeignKey(Product, verbose_name="Hàng hoá", on_delete=models.CASCADE, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, verbose_name="Kho hàng", on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField("Loại", max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField("Số lượng", max_digits=14, decimal_places=2)  # luôn dương, dấu +/- suy từ movement_type
    unit_cost = models.DecimalField("Giá vốn", max_digits=14, decimal_places=2, null=True, blank=True)  # chỉ có ý nghĩa khi Nhập
    # NCC đã bán lô hàng này cho mình (nếu nhập) — dùng lại Đối tác chung, không phải bảng riêng.
    supplier = models.ForeignKey(
        "crm.Partner", verbose_name="Nhà cung cấp", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Nếu đây là xuất kho do bán hàng — trỏ về đúng dòng Đơn hàng đã gây ra việc xuất kho này.
    reference_order_item = models.ForeignKey(
        "crm.OrderItem", verbose_name="Dòng đơn hàng liên quan",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Nhật ký kho"
        verbose_name_plural = "Nhật ký kho"

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product.sku} x{self.quantity}"
