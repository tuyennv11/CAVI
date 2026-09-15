from rest_framework.permissions import BasePermission

from accounts.roles import is_accountant, is_manager


class IsFinanceStaff(BasePermission):
    message = "Chỉ Quản lý hoặc Kế toán được xem và cập nhật tài chính đơn hàng."

    def has_permission(self, request, view):
        return is_manager(request.user) or is_accountant(request.user)
