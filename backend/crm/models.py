from django.conf import settings
from django.db import models


class Customer(models.Model):
    name = models.CharField("Tên khách hàng", max_length=255)
    company = models.CharField("Công ty", max_length=255, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=500, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Nhân viên phụ trách",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ContactLog(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contact_logs")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
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

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    note = models.CharField("Ghi chú", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Đơn #{self.pk} — {self.customer}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), start=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    description = models.CharField("Mô tả", max_length=255)
    quantity = models.DecimalField("Số lượng", max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField("Đơn giá", max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.quantity * self.unit_price
