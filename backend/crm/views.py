from datetime import timedelta

from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_manager

from rest_framework.exceptions import PermissionDenied

from .models import Activity, Notice, Order, Partner, Task, TierUpgradeRequest
from .permissions import IsAssignedOrCreatorOrManager, IsManagerOrAssignedSales
from .serializers import (
    ActivitySerializer,
    NoticeSerializer,
    OrderSerializer,
    PartnerSerializer,
    TaskSerializer,
    TierUpgradeRequestSerializer,
)

MONEY_FIELD = DecimalField(max_digits=16, decimal_places=2)

TASK_LIKE_TYPES = {
    Activity.ActivityType.TASK,
    Activity.ActivityType.FOLLOW_UP,
    Activity.ActivityType.APPOINTMENT,
    Activity.ActivityType.SUPPORT_REQUEST,
    Activity.ActivityType.COMPLAINT,
    Activity.ActivityType.ISSUE_HANDLING,
    Activity.ActivityType.POST_SALE_CARE,
}
OPEN_STATUSES = [Activity.Status.NOT_PROCESSED, Activity.Status.IN_PROGRESS]


def _sum_revenue(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(F("items__quantity") * F("items__unit_price"), output_field=MONEY_FIELD), 0, output_field=MONEY_FIELD
        )
    )["total"]


def _sum_gross_profit(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(
                F("items__quantity") * (F("items__unit_price") - F("items__unit_cost")),
                output_field=MONEY_FIELD,
            ),
            0,
            output_field=MONEY_FIELD,
        )
    )["total"]


class PartnerViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    search_fields = ["name", "contact_person", "phone"]
    filterset_fields = ["assigned_to", "partner_type"]

    def get_queryset(self):
        qs = Partner.objects.select_related("assigned_to").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(assigned_to=self.request.user)

    def perform_create(self, serializer):
        # Nhân viên kinh doanh tạo đối tác mới thì mặc định tự phụ trách đối tác đó.
        if is_manager(self.request.user) and serializer.validated_data.get("assigned_to"):
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="activities")
    def activities(self, request, pk=None):
        partner = self.get_object()
        if request.method == "GET":
            qs = partner.activities.select_related(
                "performed_by", "assigned_to", "created_by", "related_order"
            ).all()
            p = request.query_params
            if p.get("activity_type"):
                qs = qs.filter(activity_type=p["activity_type"])
            if p.get("assigned_to"):
                qs = qs.filter(assigned_to_id=p["assigned_to"])
            if p.get("performed_by"):
                qs = qs.filter(performed_by_id=p["performed_by"])
            if p.get("status"):
                qs = qs.filter(status=p["status"])
            if p.get("has_follow_up") == "true":
                qs = qs.filter(follow_up_date__isnull=False)
            elif p.get("has_follow_up") == "false":
                qs = qs.filter(follow_up_date__isnull=True)
            if p.get("date_from"):
                qs = qs.filter(activity_at__date__gte=p["date_from"])
            if p.get("date_to"):
                qs = qs.filter(activity_at__date__lte=p["date_to"])
            if p.get("search"):
                term = p["search"]
                qs = qs.filter(Q(title__icontains=term) | Q(content__icontains=term))
            return Response(ActivitySerializer(qs, many=True).data)

        data = request.data.copy()
        data["customer"] = partner.id
        serializer = ActivitySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            customer=partner,
            created_by=request.user,
            performed_by=serializer.validated_data.get("performed_by") or request.user,
        )
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"], url_path="activities/summary")
    def activities_summary(self, request, pk=None):
        partner = self.get_object()
        acts = partner.activities.all()
        today = timezone.localdate()
        last = acts.order_by("-activity_at").first()
        return Response(
            {
                "total_activities": acts.count(),
                "last_activity_at": last.activity_at if last else None,
                "upcoming_follow_ups": acts.filter(follow_up_date__isnull=False, follow_up_date__gte=today)
                .exclude(status__in=[Activity.Status.DONE, Activity.Status.CANCELLED])
                .count(),
                "unfinished_tasks": acts.filter(activity_type__in=TASK_LIKE_TYPES)
                .filter(status__in=OPEN_STATUSES)
                .count(),
            }
        )


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsAssignedOrCreatorOrManager]
    filterset_fields = ["status", "priority", "assigned_to", "partner"]

    def get_queryset(self):
        qs = Task.objects.select_related("assigned_to", "created_by", "partner").all()
        if not is_manager(self.request.user):
            qs = qs.filter(Q(assigned_to=self.request.user) | Q(created_by=self.request.user))

        p = self.request.query_params
        today = timezone.localdate()
        open_statuses = [Task.Status.TODO, Task.Status.IN_PROGRESS]
        if p.get("due") == "today":
            qs = qs.filter(due_at__date=today, status__in=open_statuses)
        elif p.get("due") == "overdue":
            qs = qs.filter(due_at__date__lt=today, status__in=open_statuses)
        elif p.get("due") == "upcoming":
            qs = qs.filter(due_at__date__gt=today, status__in=open_statuses)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TierUpgradeRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TierUpgradeRequestSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "partner"]

    def get_queryset(self):
        qs = TierUpgradeRequest.objects.select_related("partner", "requested_by", "reviewed_by").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(partner__assigned_to=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới duyệt được yêu cầu nâng hạng.")
        tier_request = self.get_object()
        tier_request.status = TierUpgradeRequest.Status.APPROVED
        tier_request.reviewed_by = request.user
        tier_request.reviewed_at = timezone.now()
        tier_request.save()
        tier_request.partner.tier_override = tier_request.requested_tier
        tier_request.partner.save(update_fields=["tier_override"])
        return Response(TierUpgradeRequestSerializer(tier_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới từ chối được yêu cầu nâng hạng.")
        tier_request = self.get_object()
        tier_request.status = TierUpgradeRequest.Status.REJECTED
        tier_request.reviewed_by = request.user
        tier_request.reviewed_at = timezone.now()
        tier_request.save()
        return Response(TierUpgradeRequestSerializer(tier_request).data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "customer", "paid", "on_platform"]

    def get_queryset(self):
        qs = Order.objects.select_related("customer", "created_by").prefetch_related("items").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(customer__assigned_to=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class NoticeViewSet(viewsets.ModelViewSet):
    """Thông báo nội bộ — ai cũng xem được, chỉ Quản lý được đăng/sửa/xoá."""

    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notice.objects.select_related("created_by").all()

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới đăng được thông báo nội bộ.")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DashboardStatsView(APIView):
    """Số liệu tổng quan cho trang Dashboard — scope theo vai trò giống các ViewSet ở trên."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        partners = Partner.objects.all()
        orders = Order.objects.all()
        acts = Activity.objects.select_related("customer", "performed_by")
        if not is_manager(request.user):
            partners = partners.filter(assigned_to=request.user)
            orders = orders.filter(customer__assigned_to=request.user)
            acts = acts.filter(customer__assigned_to=request.user)

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = orders.filter(created_at__gte=month_start)

        recent_orders = orders.select_related("customer").order_by("-created_at")[:8]
        recent_activities = acts.order_by("-activity_at")[:8]
        activity = sorted(
            [
                {
                    "type": "order",
                    "at": o.created_at,
                    "text": f"Đơn hàng #{o.id} cho {o.customer.name}",
                }
                for o in recent_orders
            ]
            + [
                {
                    "type": "contact",
                    "at": a.activity_at,
                    "text": f"{a.get_activity_type_display()} — {a.customer.name}: {a.title[:80]}",
                }
                for a in recent_activities
            ],
            key=lambda item: item["at"],
            reverse=True,
        )[:8]

        return Response(
            {
                "total_customers": partners.count(),
                "new_customers_week": partners.filter(created_at__gte=week_ago).count(),
                "orders_this_month": orders_this_month.count(),
                "revenue_this_month": _sum_revenue(orders_this_month),
                "total_revenue_all_time": _sum_revenue(orders),
                "gross_profit_this_month": _sum_gross_profit(orders_this_month),
                "gross_profit_on_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=True)
                ),
                "gross_profit_off_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=False)
                ),
                "recent_activity": activity,
            }
        )
