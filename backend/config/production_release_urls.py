from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET

from .urls import urlpatterns as application_urls


@require_GET
def release_health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        healthy = cursor.fetchone()[0] == 1
    response = JsonResponse({"environment": "production", "releaseId": settings.CAVI_RELEASE_ID,
                             "database": "ok" if healthy else "unavailable"}, status=200 if healthy else 503)
    response["Cache-Control"] = "no-store"
    return response


# TEST environment metadata, data browser and local-preview routes are absent.
urlpatterns = [
    path("api/release/", release_health),
    path("api/company-hub/", include("companyhub.urls")),
    path("api/notifications/", include("notifications.urls")),
] + application_urls
