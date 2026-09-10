from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceRecordViewSet,
    EmergencyContactViewSet,
    EmployeeDocumentViewSet,
    EmployeeViewSet,
    LeaveBalanceViewSet,
    MyProfileView,
)

router = DefaultRouter()
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("attendance", AttendanceRecordViewSet, basename="attendance")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("documents", EmployeeDocumentViewSet, basename="employee-document")
router.register("emergency-contacts", EmergencyContactViewSet, basename="emergency-contact")

urlpatterns = [
    path("profile/me/", MyProfileView.as_view(), name="my-profile"),
] + router.urls
