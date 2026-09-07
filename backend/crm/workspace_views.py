"""Các API tổng hợp cho trang "Làm việc" (Workspace) — màn hình chính nhân viên dùng hằng ngày."""

import calendar
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Activity, KPITarget, Notice, Order, Partner, Task
from .serializers import ActivitySerializer, NoticeSerializer, TaskSerializer

User = get_user_model()
MONEY_FIELD = DecimalField(max_digits=16, decimal_places=2)


def _sum_revenue(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(F("items__quantity") * F("items__unit_price"), output_field=MONEY_FIELD), 0, output_field=MONEY_FIELD
        )
    )["total"]


def _month_bounds(year, month):
    start = timezone.make_aware(datetime(year, month, 1))
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59, 999999))
    return start, end


def _pct(actual, target):
    if not target:
        return None
    return round(float(actual) / float(target) * 100)


class WorkspaceTodayView(APIView):
    """"Hôm nay của tôi" + "Việc cần chú ý" — gộp chung vì cùng mục đích: biết ngay việc cần làm."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        open_task_statuses = [Task.Status.TODO, Task.Status.IN_PROGRESS]
        open_activity_statuses = [Activity.Status.NOT_PROCESSED, Activity.Status.IN_PROGRESS]

        my_tasks = Task.objects.filter(assigned_to=user).filter(status__in=open_task_statuses)
        tasks_today = my_tasks.filter(due_at__date=today).order_by("due_at")
        tasks_overdue = my_tasks.filter(due_at__date__lt=today).order_by("due_at")

        my_activities = Activity.objects.filter(Q(performed_by=user) | Q(assigned_to=user)).distinct()
        follow_ups_due = my_activities.filter(
            follow_up_date__isnull=False, follow_up_date__lte=today
        ).exclude(status__in=[Activity.Status.DONE, Activity.Status.CANCELLED]).order_by("follow_up_date")
        appointments_today = my_activities.filter(
            activity_type__in=[Activity.ActivityType.MEETING, Activity.ActivityType.APPOINTMENT],
            activity_at__date=today,
        ).order_by("activity_at")
        calls_to_make = my_activities.filter(
            activity_type=Activity.ActivityType.CALL, status__in=open_activity_statuses
        ).order_by("activity_at")
        open_requests = my_activities.filter(
            activity_type__in=[
                Activity.ActivityType.SUPPORT_REQUEST,
                Activity.ActivityType.COMPLAINT,
                Activity.ActivityType.ISSUE_HANDLING,
            ]
        ).exclude(status__in=[Activity.Status.DONE, Activity.Status.CANCELLED]).order_by("activity_at")

        notices = Notice.objects.order_by("-created_at")[:5]

        return Response(
            {
                "tasks_today": TaskSerializer(tasks_today, many=True).data,
                "tasks_overdue": TaskSerializer(tasks_overdue, many=True).data,
                "follow_ups_due": ActivitySerializer(follow_ups_due, many=True).data,
                "appointments_today": ActivitySerializer(appointments_today, many=True).data,
                "calls_to_make": ActivitySerializer(calls_to_make, many=True).data,
                "open_requests": ActivitySerializer(open_requests, many=True).data,
                "notices": NoticeSerializer(notices, many=True).data,
            }
        )


class WorkspaceKPIView(APIView):
    """KPI + doanh thu + hiệu suất cá nhân trong tháng hiện tại."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        year, month = now.year, now.month
        today = timezone.localdate()

        month_start, month_end = _month_bounds(year, month)
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        prev_month_start, prev_month_end = _month_bounds(prev_year, prev_month)
        last_year_month_start, last_year_month_end = _month_bounds(year - 1, month)
        quarter_start_month = ((month - 1) // 3) * 3 + 1
        quarter_start, _ = _month_bounds(year, quarter_start_month)
        year_start, _ = _month_bounds(year, 1)

        my_orders = Order.objects.filter(customer__assigned_to=user).exclude(status=Order.Status.CANCELLED)

        def revenue_between(start, end=None):
            qs = my_orders.filter(created_at__gte=start)
            if end:
                qs = qs.filter(created_at__lte=end)
            return _sum_revenue(qs)

        revenue_today = revenue_between(today)
        revenue_month = revenue_between(month_start, month_end)
        revenue_quarter = revenue_between(quarter_start)
        revenue_year = revenue_between(year_start)
        revenue_prev_month = revenue_between(prev_month_start, prev_month_end)
        revenue_last_year_same_month = revenue_between(last_year_month_start, last_year_month_end)
        orders_closed_month = my_orders.filter(created_at__gte=month_start, created_at__lte=month_end).count()

        new_customers_month = Partner.objects.filter(assigned_to=user, created_at__gte=month_start).count()
        quotes_month = Activity.objects.filter(
            assigned_to=user, activity_type=Activity.ActivityType.QUOTE, activity_at__gte=month_start
        ).count()
        tasks_done_month = Task.objects.filter(
            assigned_to=user, status=Task.Status.DONE, updated_at__gte=month_start, updated_at__lte=month_end
        ).count()
        tasks_due_month = Task.objects.filter(
            assigned_to=user, due_at__gte=month_start, due_at__lte=month_end
        ).exclude(status=Task.Status.CANCELLED)
        tasks_done_ontime = tasks_due_month.filter(status=Task.Status.DONE, updated_at__lte=F("due_at")).count()
        tasks_due_count = tasks_due_month.count()

        follow_ups_month = Activity.objects.filter(
            assigned_to=user, follow_up_date__gte=month_start.date(), follow_up_date__lte=month_end.date()
        )
        follow_ups_done = follow_ups_month.filter(status=Activity.Status.DONE).count()
        follow_ups_total = follow_ups_month.count()

        target = KPITarget.objects.filter(user=user, year=year, month=month).first()
        kpi = None
        if target:
            kpi = {
                "revenue": {"actual": revenue_month, "target": target.revenue_target, "pct": _pct(revenue_month, target.revenue_target)},
                "new_customers": {"actual": new_customers_month, "target": target.new_customer_target, "pct": _pct(new_customers_month, target.new_customer_target)},
                "quotes": {"actual": quotes_month, "target": target.quote_target, "pct": _pct(quotes_month, target.quote_target)},
                "orders": {"actual": orders_closed_month, "target": target.order_target, "pct": _pct(orders_closed_month, target.order_target)},
                "tasks": {"actual": tasks_done_month, "target": target.task_target, "pct": _pct(tasks_done_month, target.task_target)},
            }

        revenue = {
            "today": revenue_today,
            "month": revenue_month,
            "quarter": revenue_quarter,
            "year": revenue_year,
            "target_month": target.revenue_target if target else None,
            "pct_month": _pct(revenue_month, target.revenue_target) if target else None,
            "vs_last_month_pct": _pct(revenue_month - revenue_prev_month, revenue_prev_month) if revenue_prev_month else None,
            "vs_last_year_pct": _pct(revenue_month - revenue_last_year_same_month, revenue_last_year_same_month)
            if revenue_last_year_same_month
            else None,
            "orders_closed_month": orders_closed_month,
        }

        task_ontime_pct = _pct(tasks_done_ontime, tasks_due_count) if tasks_due_count else None
        followup_pct = _pct(follow_ups_done, follow_ups_total) if follow_ups_total else None

        components = {}
        if kpi:
            for key, v in kpi.items():
                if v["pct"] is not None:
                    components[key] = min(v["pct"], 150)
        if task_ontime_pct is not None:
            components["task_ontime"] = min(task_ontime_pct, 150)
        if followup_pct is not None:
            components["followup"] = min(followup_pct, 150)

        performance_pct = round(sum(components.values()) / len(components)) if components else None

        return Response(
            {
                "kpi": kpi,
                "revenue": revenue,
                "performance": {
                    "overall_pct": performance_pct,
                    "task_ontime_pct": task_ontime_pct,
                    "followup_pct": followup_pct,
                    "components": components,
                },
            }
        )


class WorkspaceRankingView(APIView):
    """Bảng xếp hạng nhân viên kinh doanh trong tháng — ưu tiên KPI% (kết quả), không chỉ đếm số lượng."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        year, month = now.year, now.month
        month_start, month_end = _month_bounds(year, month)

        sales_group = Group.objects.filter(name=settings.GROUP_SALES).first()
        sales_users = sales_group.user_set.filter(is_active=True) if sales_group else User.objects.none()

        rows = []
        for u in sales_users:
            orders = Order.objects.filter(
                customer__assigned_to=u, created_at__gte=month_start, created_at__lte=month_end
            ).exclude(status=Order.Status.CANCELLED)
            revenue = _sum_revenue(orders)
            target = KPITarget.objects.filter(user=u, year=year, month=month).first()
            kpi_pct = _pct(revenue, target.revenue_target) if target else None
            tasks_done = Task.objects.filter(
                assigned_to=u, status=Task.Status.DONE, updated_at__gte=month_start, updated_at__lte=month_end
            ).count()
            new_customers = Partner.objects.filter(
                assigned_to=u, created_at__gte=month_start, created_at__lte=month_end
            ).count()
            rows.append(
                {
                    "user_id": u.id,
                    "name": u.get_full_name() or u.username,
                    "revenue": revenue,
                    "kpi_pct": kpi_pct,
                    "tasks_done": tasks_done,
                    "new_customers": new_customers,
                    "score": kpi_pct if kpi_pct is not None else 0,
                }
            )

        rows.sort(key=lambda r: r["score"], reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1

        my_rank = next((r["rank"] for r in rows if r["user_id"] == request.user.id), None)
        return Response({"ranking": rows, "my_rank": my_rank, "total": len(rows)})
