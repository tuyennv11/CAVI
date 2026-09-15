from django.conf import settings
from django.urls import include, path

from . import preview_views
from .urls import urlpatterns as application_urls

urlpatterns = [
    path("preview/data/", preview_views.index, name="preview-data"),
    path("preview/data/state/", preview_views.state, name="preview-data-state"),
    path("preview/data/api/", preview_views.api_state, name="preview-data-api"),
] + application_urls

# Optional TEST apps must not be imported under settings that do not install them.
if getattr(settings, "COMPANY_HUB_ENABLED", False):
    urlpatterns.insert(0, path("api/company-hub/", include("companyhub.urls")))
if getattr(settings, "CAVI_NOTIFICATIONS_ENABLED", False):
    urlpatterns.insert(0, path("api/notifications/", include("notifications.urls")))
