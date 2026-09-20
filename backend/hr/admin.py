from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource, ExportOnlyAdmin

from .models import (
    Department,
    EmergencyContact,
    EmployeeDocument,
    Position,
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


class DepartmentResource(ExcelModelResource):
    class Meta:
        model = Department


@admin.register(Department)
class DepartmentAdmin(ImportExportModelAdmin):
    resource_classes = [DepartmentResource]
    list_display = ("code", "name", "system_code")
    search_fields = ("code", "name", "system_code")
    readonly_fields = ("code",)


class PositionResource(ExcelModelResource):
    class Meta:
        model = Position


@admin.register(Position)
class PositionAdmin(ImportExportModelAdmin):
    resource_classes = [PositionResource]
    list_display = ("code", "name", "department", "level")
    list_filter = ("department",)
    search_fields = ("code", "name")
    readonly_fields = ("code",)
    autocomplete_fields = ["department"]


class ProfileResource(ExcelModelResource):
    class Meta:
        model = Profile
        exclude = ("avatar",)  # FileField — không xuất/nhập file qua Excel


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
        "employee_code", "username_display", "full_name_display", "preferred_name", "position",
        "department", "rooms_display", "groups_display", "job_description",
        "date_of_birth", "id_number", "phone", "country", "district", "province",
        "street_address", "ward", "avatar", "personnel_document_number", "hired_at",
        "contract_started_at", "contract_expires_at", "employment_type", "gender", "manager",
        "resigned_at", "work_location", "work_status", "education_level", "major", "skills",
    )
    # Bỏ "companies"/"Công ty" khỏi cột hiển thị + bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên giá trị
    # luôn giống nhau ở mọi dòng, không còn tác dụng lọc/phân biệt gì nữa (xem companies/admin.py).
    # Field companies vẫn giữ trong form thêm/sửa (filter_horizontal) vì logic phân quyền theo công
    # ty trong code vẫn dựa vào đó.
    list_filter = ("department", "work_status", "employment_type", "education_level")
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "phone", "id_number")
    # department chỉ hiện để xem (editable=False ở model, tự điền theo Chức vụ) — liệt kê ở đây để
    # form hiện được giá trị hiện tại thay vì ẩn hẳn đi.
    readonly_fields = ("employee_code", "department")
    filter_horizontal = ("companies", "rooms")
    inlines = [EmployeeDocumentInline, EmergencyContactInline, TrainingRecordInline]
    # Quận/Huyện, Phường/Xã có hàng trăm/hàng chục nghìn dòng — bắt buộc phải là ô tìm kiếm (autocomplete)
    # thay vì dropdown liệt kê hết, không thì không dùng nổi. `manager`/`position` cũng autocomplete
    # vì danh sách có thể lớn dần.
    autocomplete_fields = ["country", "province", "district", "ward", "manager", "position"]

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
