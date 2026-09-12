from django.db import models


class Company(models.Model):
    """1 công ty dùng chung hệ thống — hiện có đúng 1 công ty Vận chuyển (CAVI) nhưng có thể có
    NHIỀU công ty Thương mại (LIVI, AVI, sau này thêm) — thêm 1 công ty thương mại mới chỉ cần thêm
    1 dòng ở đây, không cần sửa code."""

    class BusinessType(models.TextChoices):
        TRANSPORT = "transport", "Vận chuyển"
        TRADING = "trading", "Thương mại"

    name = models.CharField("Tên công ty", max_length=100, unique=True)
    code = models.CharField("Mã công ty", max_length=20, unique=True)
    business_type = models.CharField("Loại hình", max_length=20, choices=BusinessType.choices)
    # Thông tin xuất hoá đơn/PDF — mỗi công ty có thương hiệu riêng, thay cho settings.COMPANY_HOTLINE
    # cứng dùng chung cho mọi PDF trước đây.
    legal_name = models.CharField("Tên pháp lý", max_length=255, blank=True)
    tax_code = models.CharField("Mã số thuế", max_length=20, blank=True)
    hotline = models.CharField("Hotline", max_length=32, blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    logo = models.FileField("Logo", upload_to="companies/logos/", null=True, blank=True)
    is_active = models.BooleanField("Đang hoạt động", default=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        # Theo đúng thứ tự tạo (CAVI trước, rồi LIVI, AVI...) — công ty thương mại mới thêm sau này
        # cứ nối tiếp cuối danh sách, không bị xáo trộn theo alphabet/loại hình.
        ordering = ["created_at"]
        verbose_name = "Công ty"
        verbose_name_plural = "Công ty"

    def __str__(self):
        return self.name
