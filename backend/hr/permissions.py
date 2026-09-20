from rest_framework import permissions

from accounts.roles import is_hr, is_manager


class IsManagerOrHRForWrite(permissions.BasePermission):
    """Hồ sơ nhân viên (Profile): Kế toán cần xem được (để chọn đúng người khi quản lý Lương của
    người đó) nhưng không sửa được thông tin hồ sơ chung — chỉ Quản lý/Nhân sự mới sửa được."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_manager(request.user) or is_hr(request.user)
