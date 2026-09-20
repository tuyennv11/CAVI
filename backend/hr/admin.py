from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource, ExportOnlyAdmin

from .models import (
    AttendanceRecord,
    BonusPenaltyRecord,
    CompensationRecord,
    EmergencyContact,
    EmployeeDocument,
    LeaveBalance,
    Profile,
    ProfileChangeLog,
    TrainingRecord,
)


class ProfileResource(ExcelModelResource):
    class Meta:
        model = Profile
        exclude = ("avatar",)  # FileField — không xuất/nhập file qua Excel


class LeaveBalanceResource(ExcelModelResource):
    class Meta:
        model = LeaveBalance


class AttendanceRecordResource(ExcelModelResource):
    class Meta:
        model = AttendanceRecord


class CompensationRecordResource(ExcelModelResource):
    class Meta:
        model = CompensationRecord


class BonusPenaltyRecordResource(ExcelModelResource):
    class Meta:
        model = BonusPenaltyRecord


class ProfileChangeLogResource(ExcelModelResource):
    class Meta:
        model = ProfileChangeLog


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0
    readonly_fields = ("created_by", "created_at")


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


class TrainingRecordInline(admin.TabularInline):
    model = TrainingRecord
    extra = 0
    readonly_fields = ("created_by", "created_at")


@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    resource_classes = [ProfileResource]
    # Hiện gần hết field ngay trên bảng danh sách (kiểu Excel — kéo ngang xem hết, không phải bấm
    # vào từng dòng mới thấy) — chỉ tách riêng khi dữ liệu THẬT SỰ cần tách: Lương/Thưởng-phạt (nhạy
    # cảm, khác quyền xem) đăng ký thành mục riêng bên ngoài; Giấy tờ/Liên hệ khẩn cấp/Đào tạo là
    # quan hệ 1-nhiều (1 nhân viên có nhiều dòng) nên không thể nhét vào 1 cột, để inline bên dưới
    # trang chi tiết. avatar (ảnh) không có ý nghĩa hiển thị dạng chữ nên bỏ qua ở bảng danh sách.
    list_display = (
        "employee_code", "user", "preferred_name", "gender", "job_title", "level", "department",
        "manager", "work_status", "employment_type", "phone", "date_of_birth", "id_number",
        "province", "district", "ward", "street_address", "hired_at", "resigned_at",
        "contract_type", "contract_started_at", "contract_expires_at", "work_location",
        "education_level", "major", "skills", "job_description",
    )
    # Bỏ "companies"/"Công ty" khỏi cột hiển thị + bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên giá trị
    # luôn giống nhau ở mọi dòng, không còn tác dụng lọc/phân biệt gì nữa (xem companies/admin.py).
    # Field companies vẫn giữ trong form thêm/sửa (filter_horizontal) vì logic phân quyền theo công
    # ty trong code vẫn dựa vào đó.
    list_filter = ("department", "work_status", "employment_type", "level", "education_level")
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "phone", "id_number")
    readonly_fields = ("employee_code",)
    filter_horizontal = ("companies",)
    inlines = [EmployeeDocumentInline, EmergencyContactInline, TrainingRecordInline]
    # Quận/Huyện, Phường/Xã có hàng trăm/hàng chục nghìn dòng — bắt buộc phải là ô tìm kiếm (autocomplete)
    # thay vì dropdown liệt kê hết, không thì không dùng nổi. `manager` cũng autocomplete vì danh sách
    # người dùng có thể lớn dần.
    autocomplete_fields = ["country", "province", "district", "ward", "manager"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(ImportExportModelAdmin):
    resource_classes = [LeaveBalanceResource]
    list_display = ("user", "year", "annual_current", "annual_carried", "bonus_current", "bonus_carried", "bonus_pending")
    list_filter = ("year",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(ImportExportModelAdmin):
    resource_classes = [AttendanceRecordResource]
    list_display = ("user", "date", "checked_in_at")
    list_filter = ("date",)


# Lương/Thưởng-phạt đăng ký riêng (không inline trong ProfileAdmin) — dữ liệu nhạy cảm, không nên
# hiện sẵn mỗi lần mở hồ sơ 1 nhân viên bất kỳ trong trang quản trị.
@admin.register(CompensationRecord)
class CompensationRecordAdmin(ImportExportModelAdmin):
    resource_classes = [CompensationRecordResource]
    list_display = ("profile", "effective_date", "base_salary", "allowance", "payment_method")
    list_filter = ("payment_method",)
    autocomplete_fields = ["profile"]
    readonly_fields = ("created_by", "created_at")


@admin.register(BonusPenaltyRecord)
class BonusPenaltyRecordAdmin(ImportExportModelAdmin):
    resource_classes = [BonusPenaltyRecordResource]
    list_display = ("profile", "record_type", "amount", "effective_date", "reason")
    list_filter = ("record_type",)
    autocomplete_fields = ["profile"]
    readonly_fields = ("created_by", "created_at")


# Nhật ký thay đổi — chỉ xem, không cho thêm/sửa/xoá tay trong admin vì đây là log tự động do
# signal (hr/signals.py:log_profile_changes) tạo ra. Chỉ cho Export, không cho Import (xem
# ExportOnlyAdmin ở config/admin_import_export.py) — lý do y hệt: đây là log tự động, không phải nơi
# nhập tay.
@admin.register(ProfileChangeLog)
class ProfileChangeLogAdmin(ExportOnlyAdmin, admin.ModelAdmin):
    resource_classes = [ProfileChangeLogResource]
    list_display = ("profile", "field_name", "old_value", "new_value", "changed_by", "changed_at")
    list_filter = ("field_name",)
    search_fields = ("profile__employee_code", "profile__user__username", "profile__user__first_name", "profile__user__last_name")
    autocomplete_fields = ["profile"]
    readonly_fields = ("profile", "field_name", "old_value", "new_value", "changed_by", "changed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
