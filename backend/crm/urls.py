from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DashboardStatsView, OrderViewSet, PartnerViewSet

router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="partner")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
] + router.urls
