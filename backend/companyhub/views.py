from django.conf import settings
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .calculations import FUND_REVIEWED_DIGEST, FUND_SOURCE_ID, fund_draft, payroll_components
from .models import EmployeeMaster, PayrollRecord, SourceSnapshot


class OwnerOnly(BasePermission):
    message = "Dữ liệu nguồn nhân sự chỉ mở cho chủ hệ thống; chưa cấp quyền nhân viên."

    def has_permission(self, request, view):
        return bool(getattr(settings, "COMPANY_HUB_ENABLED", False) and request.user.is_authenticated
                    and request.user.is_active and request.user.is_superuser
                    and request.user.username == getattr(settings, "COMPANY_HUB_OWNER_USERNAME", None))


class PrivateView(APIView):
    permission_classes = [OwnerOnly]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response


def latest_sources():
    newest = SourceSnapshot.objects.filter(source_id=OuterRef("source_id")).order_by("-imported_at", "-id").values("id")[:1]
    return SourceSnapshot.objects.filter(id=Subquery(newest))


def source_metadata(source):
    return {"id": source.id, "source_id": source.source_id, "title": source.title, "category": source.category,
            "period": source.period, "account": source.account, "imported_at": source.imported_at.isoformat(),
            "error_count": len(source.issues), "digest": source.digest,
            "status": "needs_review" if source.issues or source.category in {"payroll", "commission", "fund_data"} else "imported",
            "note": "Bản chụp nguồn, chưa phải quy định đã duyệt cho kỳ hiện tại."}


def page_number(request):
    try:
        number = int(request.query_params.get("page", "1"))
        if number < 1 or number > 100000:
            raise ValueError
        return number
    except ValueError:
        raise ValidationError("Số trang không hợp lệ.") from None


def paged(queryset, request, serializer):
    page = page_number(request)
    return {"count": queryset.count(), "page": page, "page_size": 20,
            "results": [serializer(item) for item in queryset[(page - 1) * 20:page * 20]]}


def employee_summary(item):
    return {"id": item.id, "code": item.code, "name": item.name, "company": item.source_company,
            "department": item.department, "job_title": item.job_title, "status": item.status,
            "source_row": item.source_row, "issue_count": len(item.issues)}


def payroll_summary(item):
    return {"id": item.id, "code": item.code, "name": item.name, "department": item.department,
            "source_row": item.source_row, "period": item.source.period, "issue_count": len(item.issues),
            "source_net_pay": item.cells.get("BC", {}).get("value"), "status": "historical_unapproved"}


class Overview(PrivateView):
    def get(self, request):
        sources = latest_sources().defer("content").order_by("category", "id")
        ids = sources.values("id")
        employees = EmployeeMaster.objects.filter(source_id__in=ids)
        return Response({"sources": [source_metadata(s) for s in sources], "employee_count": employees.count(),
                         "payroll_count": PayrollRecord.objects.filter(source_id__in=ids).count(),
                         "employee_statuses": dict(employees.values("status").annotate(total=Count("id")).values_list("status", "total")),
                         "scope": "Toàn công ty · chỉ chủ hệ thống · dữ liệu nguồn", "production_changed": False,
                         "coverage": "Chỉ bao gồm các nguồn hiển thị bên dưới; chưa hoàn tất nhập toàn bộ Drive. Nguồn chưa có sẽ được bổ sung sau khi kiểm tra.",
                         "unresolved": ["Chưa ánh xạ đầy đủ CALO/CAEX/RULO/HĐ với công ty trong app; không tự gộp.",
                                        "Bảng lương tháng 05 có lỗi tham chiếu và khác biệt công thức giữa nhân viên.",
                                        "Quy định quỹ đọc được là bản 05/11/2025; cần kiểm tra văn bản thay thế và nguồn quỹ phát sinh.",
                                        "Dữ liệu nguồn không tự cấp tài khoản, chốt lương hoặc chi thưởng; các bước này cần xác nhận riêng."]})


class Employees(PrivateView):
    def get(self, request):
        rows = EmployeeMaster.objects.filter(source__in=latest_sources()).order_by("source_row", "id")
        search = request.query_params.get("search", "").strip()[:150]
        if search:
            rows = rows.filter(Q(name__icontains=search) | Q(code__icontains=search) | Q(department__icontains=search))
        status = request.query_params.get("status")
        if status:
            rows = rows.filter(status=status)
        return Response(paged(rows, request, employee_summary))


class EmployeeDetail(PrivateView):
    def get(self, request, pk):
        item = get_object_or_404(EmployeeMaster.objects.select_related("source").defer("source__content"), pk=pk, source__in=latest_sources())
        return Response({**employee_summary(item), "fields": item.fields, "issues": item.issues, "source": source_metadata(item.source)})


class Payroll(PrivateView):
    def get(self, request):
        rows = PayrollRecord.objects.filter(source__in=latest_sources()).select_related("source").defer("source__content", "source__issues").order_by("-source__period", "source_row", "id")
        period = request.query_params.get("period")
        if period:
            rows = rows.filter(source__period=period)
        return Response(paged(rows, request, payroll_summary))


class PayrollDetail(PrivateView):
    def get(self, request, pk):
        item = get_object_or_404(PayrollRecord.objects.select_related("source"), pk=pk, source__in=latest_sources())
        sheets = item.source.content["sheets"]
        title = "LƯƠNG T05.2026" if item.source.period == "2026-05" else "LƯƠNG T06.2026"
        header = next(r for s in sheets if s["title"] == title for r in s["rows"] if r["row"] == (5 if item.source.period == "2026-05" else 1))
        fields = [{"column": col, "label": header["cells"].get(col, {}).get("value") or f"Cột {col}", **cell} for col, cell in item.cells.items()]
        calculation = payroll_components(item.cells, item.source_row) if item.source.period == "2026-05" else None
        return Response({**payroll_summary(item), "fields": fields, "issues": item.issues,
                         "source": source_metadata(item.source), "calculation": calculation})


class SourceDetail(PrivateView):
    def get(self, request, pk):
        source = get_object_or_404(latest_sources(), pk=pk)
        content = source.content
        data = {**source_metadata(source), "issues": source.issues[:100], "kind": content["kind"]}
        if content["kind"] == "document":
            data["text"] = content["text"]
        else:
            data["sheets"] = [{"title": s["title"], "rows": s["row_count"], "columns": s["column_count"]} for s in content["sheets"]]
            name = request.query_params.get("sheet")
            if name:
                sheet = next((s for s in content["sheets"] if s["title"] == name), None)
                if sheet is None:
                    raise ValidationError("Không tìm thấy trang tính trong nguồn này.")
                page = page_number(request)
                data["sheet_data"] = {"title": name, "count": len(sheet["rows"]), "page": page, "page_size": 20,
                                      "results": sheet["rows"][(page - 1) * 20:page * 20]}
        return Response(data)


class FundCalculate(PrivateView):
    def post(self, request):
        policy = latest_sources().filter(source_id=FUND_SOURCE_ID, category="fund_policy").first()
        if policy is None:
            raise ValidationError("Chưa nhập văn bản nguồn quy định quỹ.")
        if policy.digest != FUND_REVIEWED_DIGEST:
            raise ValidationError("Bản nguồn quỹ đã thay đổi. Cần kiểm chứng lại công thức trước khi tiếp tục tính.")
        try:
            return Response(fund_draft(request.data))
        except ValueError as error:
            raise ValidationError(str(error)) from None
