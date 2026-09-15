from django.urls import path

from .preview_urls import urlpatterns as preview_urls
from .staging_views import environment, health

urlpatterns = [
    path("api/environment/", environment, name="test-environment"),
    path("healthz/", health, name="test-health"),
] + preview_urls
