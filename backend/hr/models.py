from django.conf import settings
from django.db import models
from django.utils import timezone

from companies.models import Company
from geo.models import Country, District, Province, Ward


class Profile(models.Model):
    class Department(models.TextChoices):
        SALES = "sales", "Kinh doanh"
        SUPPLY = "supply", "Cung ứng"
        OPERATIONS = "operations", "Vận hành"
        ACCOUNTING = "accounting", "Kế toán"
        HR = "hr", "Nhân sự"
        MANAGEMENT = "management", "Quản lý"

    # Tách riêng 2 khái niệm khác nhau (trước đây gộp nhầm vào 1 field employment_status):
    # WorkStatus = đang/tạm/thôi làm việc; EmploymentType = hình thức hợp đồng lao động.
    class WorkStatus(models.TextChoices):
        ACTIVE = "active", "Đang làm"
        ON_LEAVE = "on_leave", "Tạm nghỉ"
        RESIGNED = "resigned", "Đã nghỉ"

    class EmploymentType(models.TextChoices):
        OFFICIAL = "official", "Chính thức"
        PROBATION = "probation", "Thử việc"
        COLLABORATOR = "collaborator", "Cộng tác viên"

    class Gender(models.TextChoices):
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        OTHER = "other", "Khác"

    class EducationLevel(models.TextChoices):
        POSTGRAD = "postgrad", "Sau đại học"
        UNIVERSITY = "university", "Đại học"
        COLLEGE = "college", "Cao đẳng"
        VOCATIONAL = "vocational", "Trung cấp"
        HIGH_SCHOOL = "high_school", "THPT"
        OTHER = "other", "Khác"

    class Level(models.TextChoices):
        CEO = "ceo", "Tổng giám đốc"
        DIRECTOR = "director", "Giám đốc"
        HEAD_OF_DEPT = "head_of_dept", "Trưởng phòng"
        DEPUTY_HEAD = "deputy_head", "Phó phòng"
        STAFF = "staff", "Nhân viên"
        INTERN = "intern", "Thực tập sinh"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="Người dùng", on_delete=models.CASCADE, related_name="profile"
    )
    # Mã nhân viên tự sinh 1 lần lúc tạo (xem save()) — không cho sửa tay.
    employee_code = models.CharField("Mã nhân viên", max_length=20, unique=True, blank=True, editable=False)
    preferred_name = models.CharField("Tên thường gọi", max_length=100, blank=True)
    gender = models.CharField("Giới tính", max_length=10, choices=Gender.choices, blank=True)
    avatar = models.FileField("Ảnh đại diện", upload_to="avatars/%Y/%m/", null=True, blank=True)
    # Nhân viên có thể thuộc NHIỀU công ty cùng lúc (vd Quản lý/Kế toán làm việc cho cả CAVI lẫn
    # LIVI) — thay cho company_code (text tự do, không có ràng buộc, không dùng ở logic nào).
    companies = models.ManyToManyField(Company, verbose_name="Công ty", related_name="staff", blank=True)
    job_title = models.CharField("Chức vụ", max_length=100, blank=True)
    level = models.CharField("Cấp bậc", max_length=20, choices=Level.choices, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người quản lý trực tiếp",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_reports"
    )
    work_location = models.CharField("Địa điểm làm việc", max_length=255, blank=True)
    job_description = models.TextField("Mô tả công việc", blank=True)
    contract_type = models.CharField("Loại hợp đồng", max_length=100, blank=True)
    contract_started_at = models.DateField("Ngày bắt đầu hợp đồng", null=True, blank=True)
    contract_expires_at = models.DateField("Ngày hết hạn hợp đồng", null=True, blank=True)
    # Phòng ban — chưa gắn với quyền hạn kỹ thuật nào (Cung ứng/Vận hành hiện chưa có nhóm quyền
    # riêng, xem accounts/roles.py và project_supply_role_deferred), chỉ là dữ liệu phân loại nhân
    # viên trước, làm nền cho khi cần tách quyền riêng theo phòng ban sau này.
    department = models.CharField("Phòng ban", max_length=20, choices=Department.choices, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    date_of_birth = models.DateField("Ngày sinh", null=True, blank=True)
    id_number = models.CharField("Số CCCD/CMND", max_length=20, blank=True)
    # Địa chỉ tách theo cấp hành chính (Quốc gia → Tỉnh/Thành → Quận/Huyện → Phường/Xã) để sau này
    # tính giá gửi hàng theo khu vực (vd theo phường) — không gộp chung 1 ô tự gõ. Quận/Huyện và
    # Phường/Xã chỉ có dữ liệu chuẩn cho Việt Nam (xem geo app); Campuchia/Lào chưa có nên để trống,
    # dùng street_address ghi chi tiết. street_address luôn là phần Đường/Số nhà, không gắn cấp nào.
    country = models.ForeignKey(
        Country, verbose_name="Quốc gia", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    province = models.ForeignKey(
        Province, verbose_name="Tỉnh/Thành phố", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    district = models.ForeignKey(
        District, verbose_name="Quận/Huyện", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    ward = models.ForeignKey(
        Ward, verbose_name="Phường/Xã", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    street_address = models.CharField("Số nhà, đường", max_length=255, blank=True)
    hired_at = models.DateField("Ngày vào làm", null=True, blank=True)
    resigned_at = models.DateField("Ngày nghỉ việc", null=True, blank=True)
    work_status = models.CharField(
        "Tình trạng nhân sự", max_length=20, choices=WorkStatus.choices, default=WorkStatus.ACTIVE
    )
    employment_type = models.CharField(
        "Loại nhân sự", max_length=20, choices=EmploymentType.choices, default=EmploymentType.OFFICIAL
    )
    education_level = models.CharField("Trình độ", max_length=20, choices=EducationLevel.choices, blank=True)
    major = models.CharField("Chuyên môn", max_length=255, blank=True)
    # Danh sách kỹ năng, cách nhau bằng dấu phẩy — chưa cần tách bảng riêng/gắn tag vì hiện chưa có
    # nhu cầu lọc/tìm kiếm theo kỹ năng, chỉ cần hiển thị trong hồ sơ.
    skills = models.TextField("Kỹ năng", blank=True)

    class Meta:
        ordering = ["employee_code"]
        verbose_name = "Hồ sơ nhân viên"
        verbose_name_plural = "Hồ sơ nhân viên"

    def __str__(self):
        return f"Hồ sơ {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.employee_code:
            # NV-00001 kiểu tăng dần đơn giản — đủ dùng cho quy mô công ty này, không cần cơ chế
            # counter riêng phức tạp hơn.
            last = Profile.objects.exclude(pk=self.pk).order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            # Dùng id kế tiếp làm số thứ tự — không trùng vì id tự tăng, dù đã có bản ghi bị xoá.
            while Profile.objects.filter(employee_code=f"NV-{next_number:05d}").exists():
                next_number += 1
            self.employee_code = f"NV-{next_number:05d}"
        super().save(*args, **kwargs)


# Field thật sự đáng ghi nhật ký khi đổi — bỏ qua employee_code (không cho sửa), avatar (file, so
# sánh text không có nghĩa), và các field kỹ thuật khác không phải quyết định nhân sự.
PROFILE_TRACKED_FIELDS = [
    "preferred_name", "gender", "job_title", "level", "manager", "work_location",
    "job_description", "contract_type", "contract_started_at", "contract_expires_at",
    "department", "phone", "date_of_birth", "id_number", "country", "province",
    "district", "ward", "street_address", "hired_at", "resigned_at", "work_status",
    "employment_type", "education_level", "major", "skills",
]


def _display_value(instance, field_name):
    field = instance._meta.get_field(field_name)
    value = getattr(instance, field_name)
    if value is None:
        return ""
    if field.choices:
        return dict(field.choices).get(value, str(value))
    return str(value)


class ProfileChangeLog(models.Model):
    """Nhật ký thay đổi hồ sơ nhân viên — 1 dòng cho mỗi field thay đổi trong 1 lần lưu (không phải
    1 dòng cho cả lần lưu), để xem đúng "trường nào đổi từ gì thành gì" như yêu cầu. Tự động ghi bởi
    signal `hr/signals.py` mỗi khi Profile.save() thay đổi field trong PROFILE_TRACKED_FIELDS — nhân
    viên không tự sửa/xoá được nhật ký này qua API (chỉ đọc)."""

    profile = models.ForeignKey(Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="change_logs")
    field_name = models.CharField("Trường thay đổi", max_length=100)
    old_value = models.TextField("Giá trị cũ", blank=True)
    new_value = models.TextField("Giá trị mới", blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người thay đổi", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    changed_at = models.DateTimeField("Thời điểm thay đổi", auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Nhật ký thay đổi hồ sơ"
        verbose_name_plural = "Nhật ký thay đổi hồ sơ"

    def __str__(self):
        return f"{self.profile.user.username}: {self.field_name} → {self.new_value}"


class EmployeeDocument(models.Model):
    """Giấy tờ/hồ sơ đính kèm nhân viên — CCCD, hợp đồng, bằng cấp, chứng chỉ... 1 bảng linh hoạt
    dùng chung, không tách field cứng riêng cho từng loại, vì mỗi nhân viên có thể có nhiều giấy tờ
    cùng loại (nhiều phụ lục hợp đồng, nhiều chứng chỉ...) và cần theo dõi ngày hết hạn + file đính kèm."""

    class DocType(models.TextChoices):
        ID_CARD = "id_card", "CCCD/CMND"
        WORK_CONTRACT = "work_contract", "Hợp đồng lao động"
        CONTRACT_APPENDIX = "contract_appendix", "Phụ lục hợp đồng"
        DEGREE = "degree", "Bằng cấp"
        CERTIFICATE = "certificate", "Chứng chỉ"
        OTHER = "other", "Khác"

    profile = models.ForeignKey(Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField("Loại giấy tờ", max_length=20, choices=DocType.choices)
    title = models.CharField("Tên giấy tờ", max_length=255)
    number = models.CharField("Số giấy tờ", max_length=100, blank=True)
    issued_at = models.DateField("Ngày cấp", null=True, blank=True)
    issued_place = models.CharField("Nơi cấp", max_length=255, blank=True)
    expires_at = models.DateField("Ngày hết hạn", null=True, blank=True)
    file = models.FileField("File đính kèm", upload_to="employee_docs/%Y/%m/", null=True, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Giấy tờ nhân viên"
        verbose_name_plural = "Giấy tờ nhân viên"

    def __str__(self):
        return f"{self.title} — {self.profile.user.username}"


class TrainingRecord(models.Model):
    """Lịch sử đào tạo — 1 dòng cho mỗi khoá học đã tham gia (khác "Lịch sử nâng bậc", vốn đã có sẵn
    qua ProfileChangeLog vì "Cấp bậc"/level nằm trong PROFILE_TRACKED_FIELDS)."""

    profile = models.ForeignKey(Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="trainings")
    course_name = models.CharField("Khoá đào tạo", max_length=255)
    started_at = models.DateField("Ngày bắt đầu", null=True, blank=True)
    ended_at = models.DateField("Ngày kết thúc", null=True, blank=True)
    trainer = models.CharField("Người/đơn vị đào tạo", max_length=255, blank=True)
    result = models.CharField("Kết quả", max_length=255, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        verbose_name = "Khoá đào tạo"
        verbose_name_plural = "Đào tạo & năng lực"

    def __str__(self):
        return f"{self.course_name} — {self.profile.user.username}"


class EmergencyContact(models.Model):
    """Người liên hệ khẩn cấp của nhân viên."""

    profile = models.ForeignKey(
        Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField("Họ tên", max_length=255)
    relationship = models.CharField("Quan hệ", max_length=100, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    note = models.TextField("Ghi chú", blank=True)

    class Meta:
        verbose_name = "Người liên hệ khẩn cấp"
        verbose_name_plural = "Người liên hệ khẩn cấp"

    def __str__(self):
        return f"{self.name} — {self.profile.user.username}"


class CompensationRecord(models.Model):
    """Lương — dữ liệu nhạy cảm, tách hẳn khỏi Profile/ProfileSerializer để chặn quyền xem theo
    từng vai trò (Quản lý/Kế toán/chính chủ) dễ dàng, không lẫn với hồ sơ chung. Mỗi lần đổi lương
    thêm 1 dòng mới theo ngày áp dụng (effective_date) thay vì ghi đè — giữ đúng lịch sử thay đổi."""

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Chuyển khoản"
        CASH = "cash", "Tiền mặt"

    profile = models.ForeignKey(
        Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="compensation_records"
    )
    effective_date = models.DateField("Ngày áp dụng")
    base_salary = models.DecimalField("Mức lương cơ bản", max_digits=14, decimal_places=2, default=0)
    allowance = models.DecimalField("Phụ cấp", max_digits=14, decimal_places=2, default=0)
    insurance_base = models.DecimalField("Mức đóng bảo hiểm", max_digits=14, decimal_places=2, default=0)
    bank_name = models.CharField("Ngân hàng", max_length=255, blank=True)
    bank_account = models.CharField("Số tài khoản nhận lương", max_length=50, blank=True)
    payment_method = models.CharField(
        "Phương thức trả lương", max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-effective_date"]
        verbose_name = "Bản ghi lương"
        verbose_name_plural = "Lương"

    def __str__(self):
        return f"Lương {self.profile.user.username} — từ {self.effective_date}"


class BonusPenaltyRecord(models.Model):
    """Thưởng/phạt/hoa hồng — phát sinh theo sự kiện (không phải mức cố định như CompensationRecord),
    cũng là dữ liệu nhạy cảm nên áp dụng đúng quyền xem như Lương."""

    class RecordType(models.TextChoices):
        BONUS = "bonus", "Thưởng"
        PENALTY = "penalty", "Phạt"
        COMMISSION = "commission", "Hoa hồng"

    profile = models.ForeignKey(
        Profile, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="bonus_penalty_records"
    )
    record_type = models.CharField("Loại", max_length=20, choices=RecordType.choices)
    amount = models.DecimalField("Số tiền", max_digits=14, decimal_places=2)
    reason = models.CharField("Lý do", max_length=255, blank=True)
    effective_date = models.DateField("Ngày áp dụng")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-effective_date"]
        verbose_name = "Thưởng/phạt/hoa hồng"
        verbose_name_plural = "Thưởng/phạt/hoa hồng"

    def __str__(self):
        return f"{self.get_record_type_display()} {self.profile.user.username} — {self.amount}"


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
