from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
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
    Room,
    TrainingRecord,
)


class RoomResource(ExcelModelResource):
    class Meta:
        model = Room


@admin.register(Room)
class RoomAdmin(ImportExportModelAdmin):
    resource_classes = [RoomResource]
    list_display = ("name",)
    search_fields = ("name",)


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


class ProfileAdminForm(forms.ModelForm):
    """Thêm field "Phân quyền" ngay trong form Hồ sơ nhân sự — đây là nhóm quyền Django thật sự nằm
    trên User (Profile.user), không phải field của Profile, nên phải khai tay + tự lưu (xem
    ProfileAdmin.save_model) thay vì admin tự xử lý như field bình thường."""

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(), required=False,
        widget=admin.widgets.FilteredSelectMultiple("Nhóm quyền", is_stacked=False),
        label="Phân quyền",
    )

    class Meta:
        model = Profile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["groups"].initial = self.instance.user.groups.all()


@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    resource_classes = [ProfileResource]
    form = ProfileAdminForm
    # Thứ tự cột khớp đúng file Excel mẫu anh gửi (Id nhân sự, Tên đăng nhập, Tên nhân sự, Tên
    # thường gọi, Chức vụ, Cấp bậc, Bộ Phận, Phòng, Phân quyền, Mô tả công việc...) — chỉ bỏ đúng 1
    # cột "Mật khẩu" vì lý do bảo mật (xem ProfileResource/ProfileAdminForm), không hiện dạng chữ ở
    # bất kỳ đâu.
    list_display = (
        "employee_code", "username_display", "full_name_display", "preferred_name", "job_title",
        "level", "department", "rooms_display", "groups_display", "job_description",
        "date_of_birth", "id_number", "phone", "country", "district", "province",
        "street_address", "ward", "avatar", "personnel_document_number", "hired_at",
        "contract_started_at", "contract_expires_at", "employment_type", "gender", "manager",
        "resigned_at", "work_location", "work_status", "education_level", "major", "skills",
    )
    # Bỏ "companies"/"Công ty" khỏi cột hiển thị + bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên giá trị
    # luôn giống nhau ở mọi dòng, không còn tác dụng lọc/phân biệt gì nữa (xem companies/admin.py).
    # Field companies vẫn giữ trong form thêm/sửa (filter_horizontal) vì logic phân quyền theo công
    # ty trong code vẫn dựa vào đó.
    list_filter = ("department", "work_status", "employment_type", "level", "education_level")
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "phone", "id_number")
    readonly_fields = ("employee_code",)
    filter_horizontal = ("companies", "rooms")
    inlines = [EmployeeDocumentInline, EmergencyContactInline, TrainingRecordInline]
    # Quận/Huyện, Phường/Xã có hàng trăm/hàng chục nghìn dòng — bắt buộc phải là ô tìm kiếm (autocomplete)
    # thay vì dropdown liệt kê hết, không thì không dùng nổi. `manager` cũng autocomplete vì danh sách
    # người dùng có thể lớn dần.
    autocomplete_fields = ["country", "province", "district", "ward", "manager"]

    @admin.display(description="Tên đăng nhập")
    def username_display(self, obj):
        return obj.user.username

    @admin.display(description="Tên nhân sự")
    def full_name_display(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Phòng")
    def rooms_display(self, obj):
        return ", ".join(r.name for r in obj.rooms.all()) or "—"

    @admin.display(description="Phân quyền")
    def groups_display(self, obj):
        return ", ".join(g.name for g in obj.user.groups.all()) or "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "groups" in form.cleaned_data:
            obj.user.groups.set(form.cleaned_data["groups"])


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
