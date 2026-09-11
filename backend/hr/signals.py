from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import PROFILE_TRACKED_FIELDS, Profile, ProfileChangeLog, _display_value


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    # Đảm bảo mọi tài khoản luôn có sẵn Hồ sơ nhân viên ngay từ lúc tạo — để Quản lý xem/sửa được
    # qua trang quản lý nhân sự dù người đó chưa từng tự đăng nhập vào trang "Hồ sơ cá nhân".
    if created:
        Profile.objects.get_or_create(user=instance)


def _raw_value(instance, field_name):
    # So sánh qua *_id cho field khoá ngoại (vd manager_id) thay vì tự dereference đối tượng liên
    # quan — tránh query DB thừa chỉ để so sánh, chỉ dereference (qua _display_value) khi đã biết
    # chắc có thay đổi thật.
    field = instance._meta.get_field(field_name)
    return getattr(instance, field.attname) if field.is_relation else getattr(instance, field_name)


@receiver(pre_save, sender=Profile)
def log_profile_changes(sender, instance, **kwargs):
    # Chỉ ghi khi SỬA (đã có pk) — tạo mới thì chưa có gì để so sánh, không phải "thay đổi".
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return

    # `_changed_by` do view gán tay trước khi gọi .save() (xem hr/views.py) — signal không tự biết
    # ai đang thao tác vì Django signal không có sẵn request.
    changed_by = getattr(instance, "_changed_by", None)

    logs = []
    for field_name in PROFILE_TRACKED_FIELDS:
        if _raw_value(old, field_name) != _raw_value(instance, field_name):
            logs.append(
                ProfileChangeLog(
                    profile=old,
                    field_name=field_name,
                    old_value=_display_value(old, field_name),
                    new_value=_display_value(instance, field_name),
                    changed_by=changed_by,
                )
            )
    if logs:
        ProfileChangeLog.objects.bulk_create(logs)
