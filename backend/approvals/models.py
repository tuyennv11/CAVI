from django.conf import settings
from django.db import models


class ApprovalRequest(models.Model):
    class RequestType(models.TextChoices):
        SETTLEMENT = "settlement", "Quyết toán"
        PROPOSAL = "proposal", "Đề xuất / Trình ký"

    class Currency(models.TextChoices):
        VND = "VND", "VNĐ"
        USD = "USD", "USD"

    class Status(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"
        PAID = "paid", "Đã chi"

    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    category = models.CharField("Danh mục", max_length=255, blank=True)
    title = models.CharField("Tiêu đề", max_length=255)
    note = models.TextField("Ghi chú", blank=True)
    # Đường dẫn tới đối tượng liên quan (vd báo giá) để người duyệt bấm vào xem đầy đủ ngữ cảnh
    # (lịch sử tương tác, báo giá...) trước khi ra quyết định, thay vì chỉ thấy 1 dòng tóm tắt.
    related_url = models.CharField("Đường dẫn liên quan", max_length=255, blank=True)
    amount = models.DecimalField("Số tiền", max_digits=16, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.VND)
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
        return f"{self.get_request_type_display()}: {self.title}"
