from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from crm.models import Order, Partner


ZERO = Decimal("0")


def next_monday_noon(completed_at):
    """Trưa thứ Hai kế tiếp, kể cả đơn hoàn tất đúng ngày thứ Hai."""
    local = timezone.localtime(completed_at)
    days = (7 - local.weekday()) % 7 or 7
    due_date = local.date() + timedelta(days=days)
    return timezone.make_aware(datetime.combine(due_date, time(hour=12)), local.tzinfo)


class OrderFinance(models.Model):
    class Currency(models.TextChoices):
        VND = "VND", "VNĐ"
        USD = "USD", "USD"
        LAK = "LAK", "Kíp Lào"
        KHR = "KHR", "Riel Campuchia"

    class ContractStatus(models.TextChoices):
        NONE = "none", "Không yêu cầu"
        REQUIRED = "required", "Cần lập"
        DRAFT = "draft", "Đang soạn"
        REVIEW = "review", "Chờ duyệt"
        SIGNED = "signed", "Đã ký"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="finance", verbose_name="Đơn hàng")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.VND, verbose_name="Tiền tệ")
    revenue_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(ZERO)], verbose_name="Doanh thu chốt")
    cargo_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(ZERO)], verbose_name="Giá trị hàng hóa")
    cargo_value_currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD, verbose_name="Tiền tệ giá trị hàng")
    exchange_rate_to_vnd = models.DecimalField(max_digits=14, decimal_places=4, default=1, validators=[MinValueValidator(Decimal("0.0001"))], verbose_name="Tỷ giá sang VNĐ")
    usd_exchange_rate_vnd = models.DecimalField(max_digits=14, decimal_places=2, default=25000, validators=[MinValueValidator(Decimal("0.01"))], verbose_name="Tỷ giá USD/VNĐ")
    deposit_required = models.BooleanField(default=False, verbose_name="Yêu cầu đặt cọc")
    deposit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(ZERO)], verbose_name="Tiền cọc yêu cầu")
    credit_terms_days = models.PositiveSmallIntegerField(default=0, verbose_name="Số ngày công nợ")
    payment_due_at = models.DateTimeField(null=True, blank=True, verbose_name="Hạn thanh toán")
    credit_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Người duyệt công nợ")
    credit_approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm duyệt công nợ")
    contract_status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.NONE, verbose_name="Trạng thái hợp đồng")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm hoàn thành")
    settlement_due_at = models.DateTimeField(null=True, blank=True, verbose_name="Hạn nộp quyết toán")
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm đã quyết toán")
    revenue_recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Người ghi nhận doanh thu")
    revenue_recorded_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm ghi nhận doanh thu")
    note = models.TextField(blank=True, verbose_name="Ghi chú tài chính")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        ordering = ["-order__created_at"]
        verbose_name = "Tài chính đơn hàng"
        verbose_name_plural = "Tài chính đơn hàng"

    def __str__(self):
        return f"Tài chính đơn #{self.order_id}"

    @property
    def effective_revenue(self):
        return self.revenue_amount or Decimal(str(self.order.total))

    @property
    def base_cost(self):
        return sum((item.quantity * item.unit_cost for item in self.order.items.all()), start=ZERO)

    @property
    def extra_cost(self):
        return sum((cost.amount_in_record_currency for cost in self.costs.all()), start=ZERO)

    @property
    def total_cost(self):
        return self.base_cost + self.extra_cost

    @property
    def collected_amount(self):
        return sum((payment.signed_amount for payment in self.payments.all()), start=ZERO)

    @property
    def recommended_deposit(self):
        pickup_cost = sum(
            (cost.amount_in_record_currency for cost in self.costs.all() if cost.category == OrderCost.Category.PICKUP),
            start=ZERO,
        )
        return pickup_cost * Decimal("0.5")

    @property
    def debt_amount(self):
        return max(self.effective_revenue - self.collected_amount, ZERO)

    @property
    def overdue_days(self):
        if not self.payment_due_at or self.debt_amount <= 0:
            return 0
        return max((timezone.localdate() - timezone.localtime(self.payment_due_at).date()).days, 0)

    @property
    def overdue_bucket(self):
        days = self.overdue_days
        if days <= 0:
            return "current"
        if days < 10:
            return "under_10"
        if days < 20:
            return "10_20"
        if days < 30:
            return "20_30"
        return "30_plus"

    @property
    def credit_approval_level(self):
        amount = self.effective_revenue
        if self.currency != self.Currency.USD:
            amount = amount * self.exchange_rate_to_vnd / self.usd_exchange_rate_vnd
        if amount <= Decimal("1000"):
            return "no_credit"
        if amount <= Decimal("2000") and self.credit_terms_days <= 15:
            return "sales_manager"
        if amount <= Decimal("10000") and self.credit_terms_days <= 45:
            return "sales_manager_director"
        return "director_ceo"

    @property
    def contract_required_by_policy(self):
        amount = self.cargo_value
        if self.cargo_value_currency != self.Currency.USD:
            amount = amount * self.exchange_rate_to_vnd / self.usd_exchange_rate_vnd
        return amount >= Decimal("5000")

    def amount_to_vnd(self, amount):
        return amount * self.exchange_rate_to_vnd


class OrderCost(models.Model):
    class Category(models.TextChoices):
        PICKUP = "pickup", "Xe lấy hàng"
        DELIVERY = "delivery", "Xe giao hàng"
        WAREHOUSE = "warehouse", "Kho bãi"
        LOADING = "loading", "Bốc xếp"
        PACKING = "packing", "Đóng gói"
        CROSS_BORDER = "cross_border", "Qua biên giới"
        CUSTOMS = "customs", "Hải quan"
        INSURANCE = "insurance", "Bảo hiểm"
        COD = "cod", "Thu hộ"
        OTHER = "other", "Khác"

    finance = models.ForeignKey(OrderFinance, on_delete=models.CASCADE, related_name="costs", verbose_name="Hồ sơ tài chính đơn hàng")
    category = models.CharField(max_length=30, choices=Category.choices, verbose_name="Loại chi phí")
    supplier = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_costs", verbose_name="Nhà cung cấp")
    description = models.CharField(max_length=255, blank=True, verbose_name="Mô tả")
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))], verbose_name="Số tiền")
    currency = models.CharField(max_length=3, choices=OrderFinance.Currency.choices, default=OrderFinance.Currency.VND, verbose_name="Tiền tệ")
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=4, default=1, validators=[MinValueValidator(Decimal("0.0001"))], verbose_name="Tỷ giá")
    incurred_at = models.DateField(default=timezone.localdate, verbose_name="Ngày phát sinh")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ["-incurred_at", "-id"]
        verbose_name = "Chi phí đơn hàng"
        verbose_name_plural = "Chi phí đơn hàng"

    @property
    def amount_in_record_currency(self):
        if self.currency == self.finance.currency:
            return self.amount
        if self.finance.currency == OrderFinance.Currency.VND:
            return self.amount * self.exchange_rate
        return self.amount / self.exchange_rate


class OrderPayment(models.Model):
    class PaymentType(models.TextChoices):
        DEPOSIT = "deposit", "Tiền cọc"
        COLLECTION = "collection", "Thu thanh toán"
        COD = "cod", "Thu hộ COD"
        REFUND = "refund", "Hoàn tiền khách"

    finance = models.ForeignKey(OrderFinance, on_delete=models.CASCADE, related_name="payments", verbose_name="Hồ sơ tài chính đơn hàng")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, verbose_name="Loại thanh toán")
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))], verbose_name="Số tiền")
    currency = models.CharField(max_length=3, choices=OrderFinance.Currency.choices, default=OrderFinance.Currency.VND, verbose_name="Tiền tệ")
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=4, default=1, validators=[MinValueValidator(Decimal("0.0001"))], verbose_name="Tỷ giá")
    paid_at = models.DateTimeField(default=timezone.now, verbose_name="Ngày thanh toán")
    reference = models.CharField(max_length=100, blank=True, verbose_name="Số tham chiếu")
    note = models.TextField(blank=True, verbose_name="Ghi chú")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="Người ghi nhận")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ["-paid_at", "-id"]
        verbose_name = "Khoản thu đơn hàng"
        verbose_name_plural = "Khoản thu đơn hàng"

    @property
    def signed_amount(self):
        amount = self.amount
        if self.currency != self.finance.currency:
            amount = amount * self.exchange_rate if self.finance.currency == OrderFinance.Currency.VND else amount / self.exchange_rate
        return -amount if self.payment_type == self.PaymentType.REFUND else amount


class OrderDocument(models.Model):
    class DocumentType(models.TextChoices):
        CONTRACT = "contract", "Hợp đồng"
        INVOICE = "invoice", "Hóa đơn"
        CUSTOMS = "customs", "Tờ khai hải quan"
        POD = "pod", "Biên bản giao hàng"
        IMAGE = "image", "Hình ảnh hàng"
        OTHER = "other", "Khác"

    finance = models.ForeignKey(OrderFinance, on_delete=models.CASCADE, related_name="documents", verbose_name="Hồ sơ tài chính đơn hàng")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, verbose_name="Loại chứng từ")
    title = models.CharField(max_length=255, verbose_name="Tiêu đề")
    file = models.FileField(upload_to="order_documents/%Y/%m/", verbose_name="File")
    document_number = models.CharField(max_length=100, blank=True, verbose_name="Số chứng từ")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="Người tải lên")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chứng từ đơn hàng"
        verbose_name_plural = "Chứng từ đơn hàng"
