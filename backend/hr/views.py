from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_manager
from crm.models import KPITarget, Order
from crm.workspace_views import _month_bounds, _pct, _sum_revenue

from .models import AttendanceRecord, EmergencyContact, EmployeeDocument, LeaveBalance, Profile
from .serializers import (
    AttendanceRecordSerializer,
    EmergencyContactSerializer,
    EmployeeDocumentSerializer,
    LeaveBalanceSerializer,
    MyProfileSerializer,
    ProfileSerializer,
)


class MyProfileView(APIView):
    """Hồ sơ cá nhân — nhân viên tự xem/sửa các field của chính mình (không sửa được field do
    Quản lý quyết định, xem MyProfileSerializer)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(MyProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = MyProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class EmployeeViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Trang quản lý nhân sự — chỉ Quản lý xem/sửa được hồ sơ của người khác."""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["employee_code", "user__username", "user__first_name", "user__last_name", "phone", "preferred_name"]
    pagination_class = None

    def get_queryset(self):
        if not is_manager(self.request.user):
            return Profile.objects.none()
        return Profile.objects.select_related(
            "user", "manager", "country", "province", "district", "ward"
        ).all()

    @action(detail=True, methods=["get"], url_path="kpi-history")
    def kpi_history(self, request, pk=None):
        # Dùng lại đúng hạ tầng KPI/doanh thu đã có ở trang "Làm việc" (WorkspaceRankingView) —
        # không tính lại kiểu khác, chỉ đổi từ "tất cả Kinh doanh tháng này" sang "1 người, nhiều tháng".
        profile = self.get_object()
        user = profile.user
        now = timezone.now()
        rows = []
        year, month = now.year, now.month
        for _ in range(6):
            month_start, month_end = _month_bounds(year, month)
            orders = Order.objects.filter(
                customer__assigned_to=user, created_at__gte=month_start, created_at__lte=month_end
            ).exclude(status=Order.Status.CANCELLED)
            revenue = _sum_revenue(orders)
            target = KPITarget.objects.filter(user=user, year=year, month=month).first()
            rows.append({
                "year": year,
                "month": month,
                "revenue": revenue,
                "revenue_target": target.revenue_target if target else None,
                "kpi_pct": _pct(revenue, target.revenue_target) if target else None,
            })
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return Response(rows)


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["profile"]

    def get_queryset(self):
        qs = EmployeeDocument.objects.select_related("profile__user")
        if is_manager(self.request.user):
            return qs
        return qs.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EmergencyContactViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["profile"]

    def get_queryset(self):
        qs = EmergencyContact.objects.select_related("profile__user")
        if is_manager(self.request.user):
            return qs
        return qs.filter(profile__user=self.request.user)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = LeaveBalance.objects.all()
        user_id = self.request.query_params.get("user")
        if is_manager(self.request.user) and user_id:
            return qs.filter(user_id=user_id)
        if is_manager(self.request.user) and not user_id:
            return qs.filter(user=self.request.user)
        return qs.filter(user=self.request.user)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = AttendanceRecord.objects.all()
        user_id = self.request.query_params.get("user")
        if is_manager(self.request.user) and user_id:
            return qs.filter(user_id=user_id)
        if is_manager(self.request.user) and not user_id:
            return qs.filter(user=self.request.user)
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        today = timezone.localdate()
        obj, created = AttendanceRecord.objects.get_or_create(
            user=self.request.user, date=today, defaults={"note": serializer.validated_data.get("note", "")}
        )
        serializer.instance = obj
