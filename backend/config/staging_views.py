from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def environment(request):
    # Public deployment metadata only, no account, DB host, secret or row counts.
    return JsonResponse({
        "application": "CAVI",
        "environment": settings.CAVI_ENVIRONMENT,
        "releaseId": settings.CAVI_RELEASE_ID,
        "apiOrigin": settings.CAVI_PUBLIC_ORIGIN,
        "nativeApiVersion": 1,
    })


@require_GET
@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        # Never leak connection errors / credentials in the health response.
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
