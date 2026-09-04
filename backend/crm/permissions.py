from rest_framework import permissions

from accounts.roles import is_manager


class IsManagerOrAssignedSales(permissions.BasePermission):
    """
    Quản lý: xem/sửa mọi khách hàng, đơn hàng.
    Nhân viên kinh doanh: chỉ xem/sửa khách hàng do mình phụ trách (và đơn hàng của khách đó).
    Object-level check backs up the queryset filtering done in each ViewSet.get_queryset().
    """

    def has_object_permission(self, request, view, obj):
        if is_manager(request.user):
            return True
        customer = obj if hasattr(obj, "assigned_to") else obj.customer
        return customer.assigned_to_id == request.user.id
