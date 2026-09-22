from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .cache_views import refresh_app

urlpatterns = [
    path("admin/", admin.site.urls),
    # Nằm dưới /api/ để Service Worker cũ (vốn loại trừ /api/) không thể
    # chặn trang phục hồi này bằng app shell đã cache.
    path("api/refresh-app/", refresh_app, name="refresh_app"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("accounts.urls")),
    path("api/", include("crm.urls")),
    path("api/", include("approvals.urls")),
    path("api/hr/", include("hr.urls")),
    path("api/geo/", include("geo.urls")),
    path("api/", include("ops.urls")),
    path("api/", include("inventory.urls")),
    path("api/", include("companies.urls")),
    path("api/finance/", include("finance.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
