from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, DashboardStatsView, OrderViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
] + router.urls
