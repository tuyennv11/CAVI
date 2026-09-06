from django.contrib import admin

from .models import AttendanceRecord, LeaveBalance, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_code", "job_title")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "annual_current", "annual_carried", "bonus_current", "bonus_carried", "bonus_pending")
    list_filter = ("year",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "checked_in_at")
    list_filter = ("date",)
