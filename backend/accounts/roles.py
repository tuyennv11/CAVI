from django.conf import settings


def is_manager(user) -> bool:
    """Quản lý: full access. Superuser/staff always counts as manager too."""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name=settings.GROUP_MANAGER).exists()
