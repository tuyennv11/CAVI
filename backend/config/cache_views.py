from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def refresh_app(request):
    """One-time recovery page for browsers controlled by a stale PWA service worker."""
    response = HttpResponse(
        """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Đang cập nhật LIVI</title>
  <style>
    body{font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:#f8f5f5;color:#241f20}
    main{text-align:center;padding:28px}h1{font-size:22px}p{color:#6e6668}
  </style>
</head>
<body><main><h1>Đang cập nhật LIVI…</h1><p>Vui lòng chờ vài giây.</p></main>
<script>
  (async () => {
    try {
      const registrations = await navigator.serviceWorker?.getRegistrations() || [];
      await Promise.all(registrations.map((registration) => registration.unregister()));
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map((name) => caches.delete(name)));
    } finally {
      location.replace('/cost-quotes?updated=' + Date.now());
    }
  })();
</script></body></html>""",
        content_type="text/html; charset=utf-8",
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Clear-Site-Data"] = '"cache"'
    return response
