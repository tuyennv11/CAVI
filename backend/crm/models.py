from django.conf import settings
from django.db import models


class Partner(models.Model):
    class PartnerType(models.TextChoices):
        CUSTOMER = "customer", "Khách hàng"
        SUPPLIER = "supplier", "Nhà cung cấp"
        BOTH = "both", "Khách hàng - Nhà cung cấp"

    class Tier(models.TextChoices):
        STANDARD = "standard", "Thường"
        VIP = "vip", "VIP"
        SUPER_VIP = "super_vip", "Siêu VIP"

    name = models.CharField("Tên", max_length=255)
    company = models.CharField("Công ty", max_length=255, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=500, blank=True)
    partner_type = models.CharField(
        "Loại đối tác", max_length=20, choices=PartnerType.choices, default=PartnerType.CUSTOMER
    )
    tier = models.CharField("Hạng", max_length=20, choices=Tier.choices, default=Tier.STANDARD)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Nhân viên phụ trách",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def credit_limit(self):
        return settings.TIER_CREDIT_LIMITS.get(self.tier, 0)

    @property
    def debt(self):
        if self.partner_type == self.PartnerType.SUPPLIER:
            return 0
        unpaid = self.orders.filter(paid=False).prefetch_related("items")
        return sum((o.total for o in unpaid), start=0)


class ContactLog(models.Model):
    class Outcome(models.TextChoices):
        PENDING = "pending", "Đang chờ"
        SUCCESS = "success", "Thành công"
        NOT_CLOSED = "not_closed", "Không chốt"
        RECEIVED = "received", "Đã nhận"

    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="contact_logs")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    contact_person = models.CharField("Người liên hệ", max_length=255, blank=True)
    outcome = models.CharField("Kết quả", max_length=20, choices=Outcome.choices, default=Outcome.PENDING)
    note = models.TextField("Nội dung chăm sóc")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} — {self.created_at:%Y-%m-%d}"


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Mới"
        PROCESSING = "processing", "Đang xử lý"
        DONE = "done", "Hoàn thành"
        CANCELLED = "cancelled", "Huỷ"

    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="orders")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    note = models.CharField("Ghi chú", max_length=500, blank=True)
    paid = models.BooleanField("Đã thanh toán", default=False)
    on_platform = models.BooleanField("Qua sàn", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Đơn #{self.pk} — {self.customer}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    @property
    def gross_profit(self):
        return sum((item.line_profit for item in self.items.all()), start=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    description = models.CharField("Mô tả", max_length=255)
    quantity = models.DecimalField("Số lượng", max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField("Đơn giá bán", max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Giá vốn", max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def line_profit(self):
        return self.quantity * (self.unit_price - self.unit_cost)
