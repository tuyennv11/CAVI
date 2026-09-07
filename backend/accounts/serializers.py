from django.conf import settings
from rest_framework import serializers

from .roles import is_manager


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
    is_manager = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return user.get_full_name() or user.username

    def get_is_manager(self, user):
        return is_manager(user)

    def get_role_label(self, user):
        return settings.GROUP_MANAGER if is_manager(user) else settings.GROUP_SALES
