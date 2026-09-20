from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    EmergencyContactViewSet,
    EmployeeDocumentViewSet,
    EmployeeViewSet,
    MyProfileView,
    PositionViewSet,
    TrainingRecordViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("positions", PositionViewSet, basename="position")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("documents", EmployeeDocumentViewSet, basename="employee-document")
router.register("emergency-contacts", EmergencyContactViewSet, basename="emergency-contact")
router.register("trainings", TrainingRecordViewSet, basename="training")

urlpatterns = [
    path("profile/me/", MyProfileView.as_view(), name="my-profile"),
] + router.urls
