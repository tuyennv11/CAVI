from django.conf import settings
from django.db import models
from django.utils import timezone


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
    contact_person = models.CharField("Người liên hệ", max_length=255, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    note = models.TextField("Mô tả thêm", blank=True)
    partner_type = models.CharField(
        "Loại đối tác", max_length=20, choices=PartnerType.choices, default=PartnerType.CUSTOMER
    )
    # Hạng do hệ thống tự tính (xem computed_tier) — chỉ bị ghi đè khi có yêu cầu nâng hạng được duyệt.
    tier_override = models.CharField(
        "Hạng đã duyệt vượt bậc", max_length=20, choices=Tier.choices, null=True, blank=True
    )
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
    def tenure_months(self):
        delta = timezone.now() - self.created_at
        return delta.days // 30

    @property
    def total_revenue(self):
        orders = self.orders.exclude(status="cancelled").prefetch_related("items")
        return sum((o.total for o in orders), start=0)

    @property
    def computed_tier(self):
        months = self.tenure_months
        revenue = self.total_revenue
        if months >= settings.TIER_TENURE_MONTHS["super_vip"] and revenue >= settings.TIER_REVENUE_THRESHOLDS["super_vip"]:
            return self.Tier.SUPER_VIP
        if months >= settings.TIER_TENURE_MONTHS["vip"] and revenue >= settings.TIER_REVENUE_THRESHOLDS["vip"]:
            return self.Tier.VIP
        return self.Tier.STANDARD

    @property
    def tier(self):
        return self.tier_override or self.computed_tier

    @property
    def tier_source(self):
        return "approved" if self.tier_override else "auto"

    @property
    def credit_limit(self):
        return settings.TIER_CREDIT_LIMITS.get(self.tier, 0)

    @property
    def debt(self):
        if self.partner_type == self.PartnerType.SUPPLIER:
            return 0
        unpaid = self.orders.filter(paid=False).prefetch_related("items")
        return sum((o.total for o in unpaid), start=0)


class TierUpgradeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Đang chờ"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="tier_requests")
    requested_tier = models.CharField("Hạng xin lên", max_length=20, choices=Partner.Tier.choices)
    reason = models.TextField("Lý do")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.partner} → {self.get_requested_tier_display()} ({self.status})"


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


class Notice(models.Model):
    code = models.CharField("Số hiệu", max_length=50, blank=True)
    title = models.CharField("Tiêu đề", max_length=255)
    body = models.TextField("Nội dung", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
