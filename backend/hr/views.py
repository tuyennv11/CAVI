from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_accountant, is_hr, is_manager
from companies.mixins import CompanyScopedMixin
from crm.models import KPITarget, Order
from crm.workspace_views import _month_bounds, _pct, _sum_revenue

from .models import (
    Department,
    EmergencyContact,
    EmployeeDocument,
    Position,
    Profile,
    TrainingRecord,
)
from .permissions import IsManagerOrHRForWrite
from .serializers import (
    DepartmentSerializer,
    EmergencyContactSerializer,
    EmployeeDocumentSerializer,
    MyProfileSerializer,
    PositionSerializer,
    ProfileSerializer,
    TrainingRecordSerializer,
)


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Danh mục Bộ phận — dùng để chọn khi sửa Hồ sơ nhân sự (giống CompanyViewSet cho companies)."""

    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Department.objects.all()
    pagination_class = None


class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """Danh mục Chức vụ — dùng để chọn khi sửa Hồ sơ nhân sự; chọn Chức vụ tự điền luôn Bộ Phận +
    Cấp bậc (xem Profile.save())."""

    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Position.objects.select_related("department")
    pagination_class = None


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
        profile._changed_by = request.user
        serializer.save()
        return Response(serializer.data)


class EmployeeViewSet(
    CompanyScopedMixin,
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """Trang quản lý nhân sự. Xem: Quản lý/Nhân sự/Kế toán xem hết (Kế toán cần thấy danh sách để
    chọn đúng người khi quản lý Lương); người khác chỉ thấy chính mình + cấp dưới trực tiếp. Sửa:
    chỉ Quản lý/Nhân sự (xem IsManagerOrHRForWrite) — Kế toán chỉ xem, không sửa hồ sơ chung."""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHRForWrite]
    search_fields = ["employee_code", "user__username", "user__first_name", "user__last_name", "phone", "preferred_name"]
    pagination_class = None

    @action(detail=False, methods=["get"], url_path=r"by-user/(?P<user_id>[1-9][0-9]*)")
    def by_user(self, request, user_id=None):
        # A user FK is not a Profile PK. Resolve only inside the caller's existing
        # visibility AND current company; never create a missing profile on GET.
        profile = get_object_or_404(
            self.get_queryset().filter(companies=self.get_active_company()), user_id=user_id
        )
        self.check_object_permissions(request, profile)
        response = Response({"id": profile.pk})
        response["Cache-Control"] = "private, no-store"
        return response

    def get_queryset(self):
        qs = Profile.objects.select_related("user", "manager", "position", "department", "country", "province", "district", "ward")
        if is_manager(self.request.user) or is_hr(self.request.user) or is_accountant(self.request.user):
            return qs.all()
        # Không có vai trò đặc biệt: chỉ thấy chính mình + những người có "Người quản lý trực
        # tiếp" (Profile.manager) trỏ tới mình — đúng nghĩa "Trưởng phòng xem nhân viên phòng
        # mình" nhưng suy ra từ quan hệ thật, không cần gán 1 vai trò riêng.
        return qs.filter(Q(user=self.request.user) | Q(manager=self.request.user))

    def perform_update(self, serializer):
        # Gán trước khi save() để signal hr/signals.py:log_profile_changes biết ai vừa sửa —
        # signal không tự có request nên phải truyền qua đây.
        serializer.instance._changed_by = self.request.user
        serializer.save()

    @action(detail=True, methods=["get"], url_path="change-log")
    def change_log(self, request, pk=None):
        profile = self.get_object()
        logs = profile.change_logs.select_related("changed_by")[:100]
        return Response([
            {
                "id": log.id,
                "field_name": log.field_name,
                "field_label": profile._meta.get_field(log.field_name).verbose_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "changed_by_name": (log.changed_by.get_full_name() or log.changed_by.username) if log.changed_by else None,
                "changed_at": log.changed_at,
            }
            for log in logs
        ])

    @action(detail=True, methods=["get"], url_path="kpi-history")
    def kpi_history(self, request, pk=None):
        # Dùng lại đúng hạ tầng KPI/doanh thu đã có ở trang "Làm việc" (WorkspaceRankingView) —
        # không tính lại kiểu khác, chỉ đổi từ "tất cả Kinh doanh tháng này" sang "1 người, nhiều tháng".
        profile = self.get_object()
        user = profile.user
        company = self.get_active_company()
        now = timezone.now()
        rows = []
        year, month = now.year, now.month
        for _ in range(6):
            month_start, month_end = _month_bounds(year, month)
            orders = Order.objects.filter(
                customer__assigned_to=user, created_at__gte=month_start, created_at__lte=month_end, company=company,
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
        if is_manager(self.request.user) or is_hr(self.request.user):
            return qs
        return qs.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TrainingRecordViewSet(viewsets.ModelViewSet):
    """Đào tạo & năng lực — xem: chính mình hoặc Quản lý/Nhân sự xem hết. Sửa: chỉ Quản lý/Nhân sự
    (giống hồ sơ chung, không nhạy cảm như Lương nên không cần tách quyền riêng cho Kế toán)."""

    serializer_class = TrainingRecordSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHRForWrite]
    filterset_fields = ["profile"]

    def get_queryset(self):
        qs = TrainingRecord.objects.select_related("profile__user")
        if is_manager(self.request.user) or is_hr(self.request.user):
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
        if is_manager(self.request.user) or is_hr(self.request.user):
            return qs
        return qs.filter(profile__user=self.request.user)


# Lương/Thưởng-phạt/Số ngày phép/Chấm công đã bị gỡ bỏ hẳn (anh yêu cầu xoá vì đang trống, sẽ sắp
# xếp lại cấu trúc dữ liệu sau) — xem hr/migrations/0022_remove_compensation_bonus_leave_attendance.py.
