"""No-op on staff/production settings. Never import optional models there."""
from django.apps import apps
from django.conf import settings


def notification_snapshot(instance, topic):
    if getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False) and apps.is_installed("notifications"):
        from notifications.service import snapshot
        return snapshot(instance, topic)
    return None


def notify_change(topic, instance, actor, before=None):
    if getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False) and apps.is_installed("notifications"):
        from notifications.service import record_change
        record_change(topic, instance, actor, before)
