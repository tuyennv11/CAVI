from django.conf import settings


def is_manager(user) -> bool:
    """Quản lý (bao gồm cả "Giám đốc" — không tách nhóm riêng, cùng nghĩa full access).
    Superuser/staff always counts as manager too."""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name=settings.GROUP_MANAGER).exists()


def is_hr(user) -> bool:
    """Nhân sự: quản lý hồ sơ chung (Profile/Giấy tờ/Liên hệ khẩn cấp) của mọi nhân viên —
    KHÔNG tự động có quyền xem Lương (xem is_accountant)."""
    return user.groups.filter(name=settings.GROUP_HR).exists()


def is_accountant(user) -> bool:
    """Kế toán: xem/sửa Lương của mọi nhân viên."""
    return user.groups.filter(name=settings.GROUP_ACCOUNTING).exists()


def is_manager_of(user, target_profile) -> bool:
    """"Trưởng phòng" không phải 1 nhóm quyền riêng — suy ra từ việc target_profile có
    Profile.manager trỏ thẳng tới user này (cấp dưới trực tiếp)."""
    return target_profile.manager_id == user.id
