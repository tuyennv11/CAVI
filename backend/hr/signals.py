from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    # Đảm bảo mọi tài khoản luôn có sẵn Hồ sơ nhân viên ngay từ lúc tạo — để Quản lý xem/sửa được
    # qua trang quản lý nhân sự dù người đó chưa từng tự đăng nhập vào trang "Hồ sơ cá nhân".
    if created:
        Profile.objects.get_or_create(user=instance)
