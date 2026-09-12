from django.conf import settings
from django.db import models

from companies.models import Company
from crm.models import Partner


class ShipmentBatch(models.Model):
    class Status(models.TextChoices):
        GATHERING = "gathering", "Đang gom hàng"
        GATHERED = "gathered", "Đã gom hàng đủ"
        SHIPPED = "shipped", "Đã gửi"

    # Nullable tạm thời — backfill CAVI ở migration rồi chuyển NOT NULL.
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, related_name="shipment_batches")
    route = models.CharField("Tuyến", max_length=50)
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.GATHERING)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người phụ trách",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chuyến gom hàng"
        verbose_name_plural = "Chuyến gom hàng"

    def __str__(self):
        return f"Chuyến {self.route} — {self.get_status_display()}"


class Shipment(models.Model):
    class KdStatus(models.TextChoices):
        NEW = "new", "Mới tạo"
        PENDING_REVIEW = "pending_review", "Chờ phòng ban duyệt"
        DONE = "done", "Hoàn tất"

    class CuStatus(models.TextChoices):
        NEW = "new", "Mới tạo"
        IN_PROGRESS = "in_progress", "Chờ cung ứng"
        DONE = "done", "Hoàn tất"

    class VhStatus(models.TextChoices):
        NEW = "new", "Mới tạo"
        PENDING = "pending", "Chờ ghi nhận"
        GATHERING = "gathering", "Đang gom hàng"
        GATHERED = "gathered", "Đã gom hàng đủ"
        SHIPPED = "shipped", "Đã gửi"

    class KtStatus(models.TextChoices):
        NOT_RECORDED = "not_recorded", "Chưa ghi nhận DT"
        RECORDED = "recorded", "Đã ghi nhận DT"

    class Currency(models.TextChoices):
        VND = "VND", "VNĐ"
        USD = "USD", "USD"

    partner = models.ForeignKey(Partner, verbose_name="Đối tác", on_delete=models.CASCADE, related_name="shipments")
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, related_name="shipments")
    description = models.CharField("Hàng hoá", max_length=255)
    route = models.CharField("Tuyến", max_length=50, blank=True)
    tracking_code = models.CharField("Mã tracking", max_length=50, blank=True, db_index=True)

    kd_status = models.CharField("Kinh doanh", max_length=20, choices=KdStatus.choices, default=KdStatus.NEW)
    cu_status = models.CharField("Cung ứng", max_length=20, choices=CuStatus.choices, default=CuStatus.NEW)
    vh_status = models.CharField("Vận hành", max_length=20, choices=VhStatus.choices, default=VhStatus.NEW)
    kt_status = models.CharField(
        "Kế toán", max_length=20, choices=KtStatus.choices, default=KtStatus.NOT_RECORDED
    )

    currency = models.CharField("Đơn vị tiền tệ", max_length=3, choices=Currency.choices, default=Currency.VND)
    amount = models.DecimalField("Số tiền", max_digits=16, decimal_places=2, default=0)

    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người phụ trách",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    batch = models.ForeignKey(
        ShipmentBatch, verbose_name="Chuyến gom hàng",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="shipments"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kiện hàng"
        verbose_name_plural = "Kiện hàng"

    def __str__(self):
        return f"Kiện #{self.pk} — {self.partner.name}"
