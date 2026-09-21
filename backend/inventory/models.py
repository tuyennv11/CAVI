from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, DecimalField, F, Sum, When

from companies.models import Company
from companies.utils import get_default_company_id


class Warehouse(models.Model):
    """Kho hàng — chỉ công ty Thương mại (LIVI, AVI...) dùng."""

    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.CASCADE, default=get_default_company_id, related_name="warehouses")
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

    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.CASCADE, default=get_default_company_id, related_name="products")
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
                    When(
                        movement_type__in=StockMovement.MovementType.decreasing_types(),
                        then=-F("quantity"),
                    ),
                    default=F("quantity"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        return agg["total"] or Decimal("0")

    def available_stock(self, warehouse=None):
        """Tồn khả dụng = Tồn thực tế - Đã giữ (InventoryReservation đang active). Giữ hàng KHÔNG
        đổi tồn thực tế (stock_on_hand ở trên), chỉ trừ ra ở đây — đúng nguyên tắc reserve tách khỏi
        xuất kho thật sự."""
        on_hand = self.stock_on_hand(warehouse)
        qs = self.reservations.filter(status=InventoryReservation.Status.ACTIVE)
        if warehouse is not None:
            qs = qs.filter(warehouse=warehouse)
        reserved = qs.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        return on_hand - reserved


class ProductImage(models.Model):
    """Hình ảnh hàng hoá — 1 sản phẩm có thể có nhiều hình hoặc không có hình nào, nên tách bảng
    riêng thay vì 1 field ảnh cứng trên Product (giống EmployeeDocument/hr.Profile)."""

    product = models.ForeignKey(Product, verbose_name="Hàng hoá", on_delete=models.CASCADE, related_name="images")
    image = models.FileField("Hình ảnh", upload_to="products/%Y/%m/")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Hình ảnh hàng hoá"
        verbose_name_plural = "Hình ảnh hàng hoá"

    def __str__(self):
        return f"Ảnh của {self.product}"


class StockMovement(models.Model):
    """Nhật ký nhập/xuất kho — tồn kho LUÔN suy ra bằng cộng dồn bảng này (nhập trừ xuất), không lưu
    field "tồn kho hiện tại" riêng ở Product — đúng nguyên tắc history-as-rows đã dùng cho Lương/
    Nhật ký thay đổi trong hệ thống này, tránh lệch số liệu giữa 2 nơi lưu cùng 1 sự thật."""

    class MovementType(models.TextChoices):
        IN = "in", "Nhập kho"
        OUT = "out", "Xuất kho"
        TRANSFER_OUT = "transfer_out", "Điều chuyển kho"
        TRANSFER_IN = "transfer_in", "Nhập điều chuyển"
        ADJUSTMENT_UP = "adjustment_up", "Điều chỉnh tăng"
        ADJUSTMENT_DOWN = "adjustment_down", "Điều chỉnh giảm"
        RETURN = "return", "Trả hàng"
        DISPOSAL = "disposal", "Huỷ hàng"

        @classmethod
        def decreasing_types(cls):
            """Loại giao dịch làm GIẢM tồn kho — dùng chung cho Product.stock_on_hand(). Mọi loại
            còn lại (Nhập kho/Nhập điều chuyển/Điều chỉnh tăng/Trả hàng) làm TĂNG tồn kho. quantity
            luôn dương ở mọi loại (chiều +/- suy hoàn toàn từ movement_type, không còn cho phép số
            âm ở Điều chỉnh như trước)."""
            return {cls.OUT, cls.TRANSFER_OUT, cls.ADJUSTMENT_DOWN, cls.DISPOSAL}

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
    # Truy vết Nhập mua về đúng Lô hàng — biết được giá vốn/nhà cung cấp/thời điểm giao của số hàng
    # nhập này, phục vụ tính bình quân gia quyền theo Kho+Sản phẩm (xem Lot.unit_cost).
    lot = models.ForeignKey(
        "Lot", verbose_name="Lô hàng", on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
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


class Lot(models.Model):
    """Lô hàng — mỗi đợt giao hàng thực tế từ 1 dòng Đề nghị mua (crm.PurchaseRequestItem). 1 Đề
    nghị mua có thể chia thành nhiều Lô (giao nhiều đợt); giá vốn tính RIÊNG theo từng Lô (xem
    LotCost/unit_cost bên dưới) — KHÔNG lưu 1 giá vốn cố định chung ở Product."""

    code = models.CharField("Mã lô", max_length=20, unique=True, blank=True, editable=False)
    purchase_request_item = models.ForeignKey(
        "crm.PurchaseRequestItem", verbose_name="Dòng đề nghị mua", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="lots"
    )
    product = models.ForeignKey(Product, verbose_name="Hàng hoá", on_delete=models.CASCADE, related_name="lots")
    supplier = models.ForeignKey(
        "crm.Partner", verbose_name="Nhà cung cấp", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    quantity = models.DecimalField("Số lượng", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("Giá mua", max_digits=14, decimal_places=2, default=0)
    origin_point = models.CharField("Điểm xuất phát", max_length=255, blank=True)
    warehouse = models.ForeignKey(
        Warehouse, verbose_name="Kho nhận", on_delete=models.SET_NULL, null=True, blank=True, related_name="lots"
    )
    shipped_at = models.DateField("Ngày giao", null=True, blank=True)
    received_at = models.DateField("Ngày nhập kho", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lô hàng"
        verbose_name_plural = "Lô hàng"

    def __str__(self):
        return f"{self.code} — {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            last = Lot.objects.exclude(pk=self.pk).order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            while Lot.objects.filter(code=f"LO{next_number:06d}").exists():
                next_number += 1
            self.code = f"LO{next_number:06d}"
        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        """Tổng giá vốn lô = tổng mọi dòng LotCost (Tiền hàng + Vận chuyển + Hải quan + Chi phí
        khác) — tính động, KHÔNG lưu cứng."""
        return sum((c.amount for c in self.costs.all()), start=Decimal("0"))

    @property
    def unit_cost(self):
        if not self.quantity:
            return Decimal("0")
        return self.total_cost / self.quantity


class LotCost(models.Model):
    """1 dòng chi phí cấu thành giá vốn của 1 Lô — nhiều dòng/lô, cộng lại ra Lot.total_cost."""

    class Category(models.TextChoices):
        HANG_HOA = "hang_hoa", "Tiền hàng"
        VAN_CHUYEN = "van_chuyen", "Vận chuyển"
        HAI_QUAN = "hai_quan", "Hải quan"
        KHAC = "khac", "Chi phí khác"

    lot = models.ForeignKey(Lot, verbose_name="Lô hàng", on_delete=models.CASCADE, related_name="costs")
    category = models.CharField("Loại chi phí", max_length=20, choices=Category.choices)
    amount = models.DecimalField("Số tiền", max_digits=16, decimal_places=2)
    note = models.CharField("Ghi chú", max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chi phí lô hàng"
        verbose_name_plural = "Chi phí lô hàng"

    def __str__(self):
        return f"{self.get_category_display()}: {self.amount}"


class InventoryReservation(models.Model):
    """Giữ hàng cho 1 dòng Yêu cầu giá — tách khỏi tồn thực tế. Tồn thực tế (Product.stock_on_hand)
    KHÔNG đổi khi giữ hàng, chỉ Tồn khả dụng (Product.available_stock) giảm."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Đang giữ"
        RELEASED = "released", "Đã huỷ giữ"
        CONSUMED = "consumed", "Đã xuất kho"

    product = models.ForeignKey(Product, verbose_name="Hàng hoá", on_delete=models.CASCADE, related_name="reservations")
    warehouse = models.ForeignKey(Warehouse, verbose_name="Kho hàng", on_delete=models.CASCADE, related_name="reservations")
    quantity = models.DecimalField("Số lượng giữ", max_digits=14, decimal_places=2)
    price_request_item = models.ForeignKey(
        "crm.PriceRequestItem", verbose_name="Dòng yêu cầu giá", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reservations"
    )
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    released_at = models.DateTimeField("Thời điểm huỷ giữ", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Giữ hàng"
        verbose_name_plural = "Giữ hàng"

    def __str__(self):
        return f"{self.product.sku} x{self.quantity} ({self.get_status_display()})"
