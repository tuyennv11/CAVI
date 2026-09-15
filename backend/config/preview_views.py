"""Authenticated data viewer, mounted only by preview_settings."""

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

owner_required = user_passes_test(lambda user: user.is_active and user.is_superuser, login_url="/admin/login/")


TABLES = {
    "companies.company": ("Công ty", [("id", "ID"), ("code", "Mã"), ("name", "Tên công ty")]),
    "crm.partner": ("Đối tác", [("id", "ID"), ("name", "Tên"), ("is_customer", "Khách hàng"), ("is_supplier", "Nhà cung cấp")]),
    "crm.order": ("Đơn hàng", [("id", "ID"), ("company_id", "Công ty ID"), ("customer_id", "Khách ID"), ("status", "Trạng thái"), ("total", "Giá trị đơn"), ("paid", "Đã thu đủ")]),
    "finance.orderfinance": ("Tài chính đơn hàng", [("id", "ID"), ("order_id", "Đơn ID"), ("currency", "Tiền tệ"), ("effective_revenue", "Giá trị"), ("total_cost", "Chi phí"), ("collected_amount", "Đã thu"), ("debt_amount", "Còn phải thu"), ("note", "Ghi chú")]),
    "finance.ordercost": ("Chi phí", [("id", "ID"), ("finance_id", "Hồ sơ tài chính ID"), ("category", "Loại"), ("description", "Diễn giải"), ("amount", "Số tiền"), ("currency", "Tiền tệ")]),
    "finance.orderpayment": ("Khoản thu", [("id", "ID"), ("finance_id", "Hồ sơ tài chính ID"), ("payment_type", "Loại"), ("amount", "Số tiền"), ("currency", "Tiền tệ"), ("reference", "Tham chiếu")]),
    "finance.orderdocument": ("Chứng từ", [("id", "ID"), ("finance_id", "Hồ sơ tài chính ID"), ("document_type", "Loại"), ("title", "Tên chứng từ")]),
    "ops.shipment": ("Kiện hàng", [("id", "ID"), ("tracking_code", "Mã vận đơn"), ("description", "Hàng hóa"), ("route", "Tuyến"), ("vh_status", "Vận hành")]),
}


@never_cache
@owner_required
def index(request):
    return render(request, "preview/data.html", {
        "tables": [(key, value[0]) for key, value in TABLES.items()],
        "app_url": getattr(settings, "PREVIEW_APP_URL", "/"),
    })


@never_cache
@owner_required
def state(request):
    return data_response(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_state(request):
    # The cross-company viewer is for the preview owner, not every staff member.
    if not request.user.is_superuser:
        response = JsonResponse({"detail": "Chỉ chủ bản xem thử được xem bảng dữ liệu này."}, status=403)
        response["Cache-Control"] = "no-store"
        return response
    return data_response(request)


def data_response(request):
    key = request.GET.get("table", "crm.order")
    if key not in TABLES:
        return JsonResponse({"error": "Bảng không có trong bản xem thử."}, status=400)
    label, columns = TABLES[key]
    model = apps.get_model(key)
    queryset = model.objects.order_by("-pk")
    if key == "crm.order":
        queryset = queryset.prefetch_related("items")
    elif key == "finance.orderfinance":
        queryset = queryset.select_related("order").prefetch_related("order__items", "costs", "payments")
    rows = []
    for obj in queryset[:50]:
        cells = []
        for field, _ in columns:
            value = getattr(obj, field)
            if isinstance(value, bool):
                value = "Có" if value else "Không"
            elif value is None:
                value = "—"
            else:
                value = str(value)
            cells.append(value)
        rows.append({"id": obj.pk, "cells": cells})
    response = JsonResponse({
        "title": label,
        "table": key,
        "columns": [label for _, label in columns],
        "rows": rows,
        "counts": [{"key": name, "title": spec[0], "count": apps.get_model(name).objects.count()} for name, spec in TABLES.items()],
        "admin_url": reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"),
        "updated_at": timezone.localtime().isoformat(),
    })
    response["Cache-Control"] = "no-store"
    return response
