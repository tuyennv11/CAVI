from django.conf import settings
from rest_framework import serializers

from companies.models import Company

from .roles import is_accountant, is_hr, is_manager, is_supply


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return user.get_full_name() or user.username


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    profile_id = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()
    is_hr = serializers.SerializerMethodField()
    is_accountant = serializers.SerializerMethodField()
    is_supply = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    companies = serializers.SerializerMethodField()
    can_view_company_hub = serializers.SerializerMethodField()
    can_use_notifications = serializers.SerializerMethodField()

    def get_can_use_notifications(self, user):
        return bool(getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False) and user.is_active)

    def get_can_view_company_hub(self, user):
        return bool(getattr(settings, "COMPANY_HUB_ENABLED", False) and user.is_active and user.is_superuser
                    and user.username == getattr(settings, "COMPANY_HUB_OWNER_USERNAME", None))

    def get_full_name(self, user):
        return user.get_full_name() or user.username

    def get_profile_id(self, user):
        # Không phải User nào cũng có hr.Profile liên kết (vd superuser kỹ thuật) — trả None thay vì
        # để lỗi 500, để frontend biết "không phải Kinh doanh nào" mà ẩn nút liên quan.
        profile = getattr(user, "profile", None)
        return profile.id if profile else None

    def get_is_manager(self, user):
        return is_manager(user)

    def get_is_hr(self, user):
        return is_hr(user)

    def get_is_accountant(self, user):
        return is_accountant(user)

    def get_is_supply(self, user):
        return is_supply(user)

    def get_role_label(self, user):
        # 1 người có thể thuộc nhiều nhóm cùng lúc (vd vừa Kế toán vừa Nhân viên kinh doanh) —
        # ghép hết các vai trò thật sự có, không chỉ chọn 1.
        if is_manager(user):
            return settings.GROUP_MANAGER
        labels = [g.name for g in user.groups.all()] or [settings.GROUP_SALES]
        return " · ".join(labels)

    def get_companies(self, user):
        # Quản lý được chọn bất kỳ công ty nào (đúng nghĩa full-access), không giới hạn theo
        # Profile.companies đã gán tay — người khác chỉ chọn được công ty mình thuộc về.
        if is_manager(user):
            qs = Company.objects.filter(is_active=True)
        else:
            qs = user.profile.companies.filter(is_active=True)
        return [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "business_type": c.business_type,
                "logo": c.logo.url if c.logo else None,
            }
            for c in qs
        ]
