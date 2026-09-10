from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    class Department(models.TextChoices):
        SALES = "sales", "Kinh doanh"
        SUPPLY = "supply", "Cung ứng"
        OPERATIONS = "operations", "Vận hành"
        ACCOUNTING = "accounting", "Kế toán"
        HR = "hr", "Nhân sự"
        MANAGEMENT = "management", "Quản lý"

    class EmploymentStatus(models.TextChoices):
        PROBATION = "probation", "Đang thử việc"
        ACTIVE = "active", "Đang làm việc"
        RESIGNED = "resigned", "Đã nghỉ việc"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="Người dùng", on_delete=models.CASCADE, related_name="profile"
    )
    company_code = models.CharField("Mã công ty", max_length=50, default="CAVI")
    job_title = models.CharField("Chức vụ", max_length=100, blank=True)
    # Phòng ban — chưa gắn với quyền hạn kỹ thuật nào (Cung ứng/Vận hành hiện chưa có nhóm quyền
    # riêng, xem accounts/roles.py và project_supply_role_deferred), chỉ là dữ liệu phân loại nhân
    # viên trước, làm nền cho khi cần tách quyền riêng theo phòng ban sau này.
    department = models.CharField("Phòng ban", max_length=20, choices=Department.choices, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    date_of_birth = models.DateField("Ngày sinh", null=True, blank=True)
    id_number = models.CharField("Số CCCD/CMND", max_length=20, blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    hired_at = models.DateField("Ngày vào làm", null=True, blank=True)
    employment_status = models.CharField(
        "Trạng thái làm việc", max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )

    class Meta:
        verbose_name = "Hồ sơ nhân viên"
        verbose_name_plural = "Hồ sơ nhân viên"

    def __str__(self):
        return f"Hồ sơ {self.user.username}"


class LeaveBalance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="leave_balances"
    )
    year = models.PositiveIntegerField("Năm")
    annual_current = models.DecimalField("Phép năm nay", max_digits=5, decimal_places=1, default=0)
    annual_carried = models.DecimalField("Phép năm cũ", max_digits=5, decimal_places=1, default=0)
    bonus_current = models.DecimalField("Phép tăng thêm năm nay", max_digits=5, decimal_places=1, default=0)
    bonus_carried = models.DecimalField("Phép tăng thêm năm cũ", max_digits=5, decimal_places=1, default=0)
    bonus_pending = models.DecimalField("Phép tăng thêm chờ phân bổ", max_digits=5, decimal_places=1, default=0)

    class Meta:
        unique_together = ["user", "year"]
        verbose_name = "Số ngày phép"
        verbose_name_plural = "Số ngày phép"

    def __str__(self):
        return f"Phép {self.user.username} — {self.year}"

    @property
    def total_available(self):
        return self.annual_current + self.annual_carried + self.bonus_current + self.bonus_carried


class AttendanceRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Nhân viên",
        on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField("Ngày", default=timezone.localdate)
    checked_in_at = models.DateTimeField("Giờ chấm công", auto_now_add=True)
    note = models.CharField("Ghi chú", max_length=255, blank=True)

    class Meta:
        unique_together = ["user", "date"]
        ordering = ["-date"]
        verbose_name = "Bản ghi chấm công"
        verbose_name_plural = "Bản ghi chấm công"

    def __str__(self):
        return f"{self.user.username} — {self.date}"
