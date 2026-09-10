from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceRecordViewSet,
    BonusPenaltyRecordViewSet,
    CompensationRecordViewSet,
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
router.register("compensation", CompensationRecordViewSet, basename="compensation")
router.register("bonus-penalty", BonusPenaltyRecordViewSet, basename="bonus-penalty")

urlpatterns = [
    path("profile/me/", MyProfileView.as_view(), name="my-profile"),
] + router.urls
