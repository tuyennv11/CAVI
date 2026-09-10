from django.contrib import admin

from .models import AttendanceRecord, LeaveBalance, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "department", "phone", "employment_status", "hired_at")
    list_filter = ("department", "employment_status")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone", "id_number")
    # Quận/Huyện, Phường/Xã có hàng trăm/hàng chục nghìn dòng — bắt buộc phải là ô tìm kiếm (autocomplete)
    # thay vì dropdown liệt kê hết, không thì không dùng nổi.
    autocomplete_fields = ["country", "province", "district", "ward"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "annual_current", "annual_carried", "bonus_current", "bonus_carried", "bonus_pending")
    list_filter = ("year",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "checked_in_at")
    list_filter = ("date",)
