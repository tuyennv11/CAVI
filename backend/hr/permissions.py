from rest_framework import permissions

from accounts.roles import is_accountant, is_hr, is_manager


class IsAccountantOrManagerForWrite(permissions.BasePermission):
    """Lương/Thưởng-phạt: ai cũng xem được record của chính mình (queryset đã tự lọc ở
    get_queryset), nhưng chỉ Kế toán/Quản lý mới tạo/sửa/xoá được — kể cả cho chính hồ sơ của họ,
    tránh tự sửa lương của mình."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_manager(request.user) or is_accountant(request.user)


class IsManagerOrHRForWrite(permissions.BasePermission):
    """Hồ sơ nhân viên (Profile): Kế toán cần xem được (để chọn đúng người khi quản lý Lương của
    người đó) nhưng không sửa được thông tin hồ sơ chung — chỉ Quản lý/Nhân sự mới sửa được."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_manager(request.user) or is_hr(request.user)
