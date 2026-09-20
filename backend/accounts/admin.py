"""Đăng ký lại User/Group của Django (mặc định do django.contrib.auth.admin tự đăng ký khi
autodiscover chạy admin.py) — chỉ để mở Export Excel, KHÔNG cho Nhập (tài khoản đăng nhập/mật khẩu/
nhóm quyền phải qua đúng luồng có xác thực của Django, không sửa qua Excel)."""

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from config.admin_import_export import ExcelModelResource, ExportOnlyAdmin


class UserResource(ExcelModelResource):
    class Meta:
        model = User
        exclude = ("password",)  # tuyệt đối không xuất mã băm mật khẩu ra file Excel


class GroupResource(ExcelModelResource):
    class Meta:
        model = Group


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserExportAdmin(ExportOnlyAdmin, UserAdmin):
    resource_classes = [UserResource]


@admin.register(Group)
class GroupExportAdmin(ExportOnlyAdmin, GroupAdmin):
    resource_classes = [GroupResource]
