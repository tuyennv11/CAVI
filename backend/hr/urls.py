from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AttendanceRecordViewSet, LeaveBalanceViewSet, MyProfileView

router = DefaultRouter()
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("attendance", AttendanceRecordViewSet, basename="attendance")

urlpatterns = [
    path("profile/me/", MyProfileView.as_view(), name="my-profile"),
] + router.urls
