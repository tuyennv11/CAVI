from django.contrib import admin

from .models import (
    AttendanceRecord,
    BonusPenaltyRecord,
    CompensationRecord,
    EmergencyContact,
    EmployeeDocument,
    LeaveBalance,
    Profile,
)


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0
    readonly_fields = ("created_by", "created_at")


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "employee_code", "user", "preferred_name", "job_title", "department", "manager",
        "work_status", "employment_type", "hired_at",
    )
    list_filter = ("department", "work_status", "employment_type")
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "phone", "id_number")
    readonly_fields = ("employee_code",)
    inlines = [EmployeeDocumentInline, EmergencyContactInline]
    # Quận/Huyện, Phường/Xã có hàng trăm/hàng chục nghìn dòng — bắt buộc phải là ô tìm kiếm (autocomplete)
    # thay vì dropdown liệt kê hết, không thì không dùng nổi. `manager` cũng autocomplete vì danh sách
    # người dùng có thể lớn dần.
    autocomplete_fields = ["country", "province", "district", "ward", "manager"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "annual_current", "annual_carried", "bonus_current", "bonus_carried", "bonus_pending")
    list_filter = ("year",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "checked_in_at")
    list_filter = ("date",)


# Lương/Thưởng-phạt đăng ký riêng (không inline trong ProfileAdmin) — dữ liệu nhạy cảm, không nên
# hiện sẵn mỗi lần mở hồ sơ 1 nhân viên bất kỳ trong trang quản trị.
@admin.register(CompensationRecord)
class CompensationRecordAdmin(admin.ModelAdmin):
    list_display = ("profile", "effective_date", "base_salary", "allowance", "payment_method")
    list_filter = ("payment_method",)
    autocomplete_fields = ["profile"]
    readonly_fields = ("created_by", "created_at")


@admin.register(BonusPenaltyRecord)
class BonusPenaltyRecordAdmin(admin.ModelAdmin):
    list_display = ("profile", "record_type", "amount", "effective_date", "reason")
    list_filter = ("record_type",)
    autocomplete_fields = ["profile"]
    readonly_fields = ("created_by", "created_at")
