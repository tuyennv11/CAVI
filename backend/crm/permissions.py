from rest_framework import permissions

from accounts.roles import is_manager, is_supply


class IsManagerOrAssignedSales(permissions.BasePermission):
    """
    Quản lý: xem/sửa mọi khách hàng, đơn hàng.
    Nhân viên kinh doanh: chỉ xem/sửa khách hàng do mình phụ trách (và đơn hàng của khách đó).
    Object-level check backs up the queryset filtering done in each ViewSet.get_queryset().
    """

    def has_object_permission(self, request, view, obj):
        if is_manager(request.user):
            return True
        if hasattr(obj, "assigned_to"):
            partner = obj
        elif hasattr(obj, "customer"):
            partner = obj.customer
        else:
            partner = obj.partner
        return partner.assigned_to_id == request.user.id


class IsAssignedOrCreatorOrManager(permissions.BasePermission):
    """Công việc: Quản lý xem hết; nhân viên chỉ xem việc mình phụ trách hoặc mình giao."""

    def has_object_permission(self, request, view, obj):
        if is_manager(request.user):
            return True
        return obj.assigned_to_id == request.user.id or obj.created_by_id == request.user.id


class IsManagerOrSupply(permissions.BasePermission):
    """Sàn báo giá cạnh tranh: Quản lý và Cung ứng đều xem được hết (đúng nghĩa cạnh tranh toàn
    công ty, không giới hạn theo Hỏi giá mình phụ trách). Xoá 1 báo giá đã chào: Quản lý xoá được
    của ai cũng được, Cung ứng khác chỉ xoá được báo giá CỦA CHÍNH MÌNH (rút lại) — không xoá được
    của người khác."""

    def has_permission(self, request, view):
        return is_manager(request.user) or is_supply(request.user)

    def has_object_permission(self, request, view, obj):
        if is_manager(request.user):
            return True
        return obj.bidder_id == request.user.id
