"""Owner-only, company-scoped live projections, read-only and TEST-local only."""
import re
from datetime import date, datetime, time
from decimal import Decimal, localcontext

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from companies.utils import get_active_company
from crm.models import Order
from finance.models import OrderFinance
from .funds import METHODS, ZERO, allocate, allocation_index, number, policy_info, profit_bands
from .views import PrivateView, page_number

MAX_ORDERS = 2000


def period_bounds(value):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value or ""):
        raise ValidationError("Kỳ phải theo dạng YYYY-MM.")
    try:
        start = date.fromisoformat(value + "-01")
        end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    except ValueError:
        raise ValidationError("Kỳ không hợp lệ.") from None
    return [timezone.make_aware(datetime.combine(day, time.min)) for day in (start, end)]


def positive_money(value, *, zero=True):
    return isinstance(value, Decimal) and value.is_finite() and (value >= 0 if zero else value > 0)


def order_projection(order, method):
    result = {"order_id": order.pk, "order_code": f"{order.company.code}-{order.pk:06d}",
              "customer_id": order.customer_id, "customer_name": order.customer.name,
              "finance_id": None, "status": "waiting", "reasons": [], "below": None, "above": None,
              "gross_profit": None, "revenue": None, "floor": None, "cost": None, "receipt_total": None,
              "is_example": False, "ready_at": None}
    reasons = result["reasons"]
    try:
        finance = order.finance
    except OrderFinance.DoesNotExist:
        reasons.append("Chưa có hồ sơ tài chính đơn hàng.")
        return result
    result["finance_id"] = finance.pk
    result["ready_at"] = finance.completed_at.isoformat() if finance.completed_at else None
    if order.status == Order.Status.CANCELLED:
        reasons.append("Đơn đã hủy; không cộng phân bổ.")
        return result
    if order.status != Order.Status.DONE or not finance.completed_at:
        reasons.append("Đơn chưa hoàn thành.")
    if not finance.settled_at:
        reasons.append("Chưa quyết toán chi phí, gồm chi phí bán hàng/lãi công nợ nếu có.")
    if not finance.revenue_recorded_at:
        reasons.append("Chưa ghi nhận doanh thu chốt.")
    # Order currency is not stored separately from finance; support only the
    # verified VND case. Mixed-currency conversions require a separate policy.
    if finance.currency != "VND":
        reasons.append("Chưa xác minh giá sàn/giá vốn và tỷ giá cho đơn không dùng VND.")
        return result
    items, costs, payments = list(order.items.all()), list(finance.costs.all()), list(finance.payments.all())
    invalid_inputs = False
    if not items or any(not positive_money(i.quantity, zero=False) or not positive_money(i.unit_cost, zero=False) for i in items):
        reasons.append("Thiếu giá vốn đáng tin cậy: giá vốn 0 mặc định chưa được coi là chi phí thật bằng 0.")
        invalid_inputs = True
    if order.floor_price is None or not positive_money(order.floor_price):
        reasons.append("Chưa có giá sàn hợp lệ đã lưu trên đơn; không suy ngược từ tỷ lệ hiện tại.")
        invalid_inputs = True
    if not positive_money(finance.revenue_amount):
        reasons.append("Doanh thu chốt không hợp lệ.")
        invalid_inputs = True
    if any(c.currency != "VND" or not positive_money(c.amount) for c in costs):
        reasons.append("Chi phí bổ sung có tiền tệ khác hoặc số liệu không hợp lệ.")
        invalid_inputs = True
    service_payments = [p for p in payments if p.payment_type != "cod"]
    if any(p.currency != "VND" or not positive_money(p.amount) or p.payment_type not in {"deposit", "collection", "refund"}
           for p in service_payments):
        reasons.append("Khoản thu/hoàn tiền cần đối chiếu tiền tệ và loại khoản thu.")
        invalid_inputs = True
    now = timezone.now()
    if any(p.paid_at > now for p in service_payments):
        reasons.append("Có khoản thu ghi ngày tương lai; chưa coi là thực thu.")
    if ((finance.completed_at and finance.completed_at > now)
            or (finance.settled_at and finance.settled_at > now)
            or (finance.revenue_recorded_at and finance.revenue_recorded_at > now)):
        reasons.append("Ngày hoàn thành/quyết toán ở tương lai.")
    if any(c.incurred_at > timezone.localdate() for c in costs):
        reasons.append("Có chi phí ghi ngày tương lai; cần đối chiếu trước khi tính quỹ.")
    # Do not use effective_revenue: its `or` fallback erases an explicit zero.
    if finance.revenue_recorded_at and positive_money(finance.revenue_amount):
        result["revenue"] = number(finance.revenue_amount)
    if order.floor_price is not None and positive_money(order.floor_price):
        result["floor"] = number(order.floor_price)
    if invalid_inputs:
        return result
    with localcontext() as ctx:
        ctx.prec = 50
        receipts = sum((-p.amount if p.payment_type == "refund" else p.amount for p in service_payments), ZERO)
        cost = sum((i.quantity * i.unit_cost for i in items), ZERO) + sum((c.amount for c in costs), ZERO)
        result.update(receipt_total=number(receipts), cost=number(cost))
        if receipts != finance.revenue_amount:
            reasons.append("Thực thu dịch vụ chưa khớp doanh thu chốt (không tính COD); cần thu đủ hoặc đối chiếu thu thừa/hoàn tiền.")
        if reasons:
            return result
        below, above = profit_bands(receipts, order.floor_price, cost, method)
        result.update(below=number(below), above=number(above), gross_profit=number(below + above))
        if below < 0 or above < 0:
            reasons.append("Có phần lợi nhuận âm/giá bán dưới sàn: giữ nguyên số để đối chiếu, chưa tự trừ hoặc phân bổ quỹ.")
            result["status"] = "review"
        else:
            result["status"] = "calculated"
        return result


def example_projection(method):
    below, above = profit_bands(Decimal(12000000), Decimal(10000000), Decimal(8000000), method)
    return [{"order_id": None, "order_code": "Đơn minh họa", "customer_id": None,
             "customer_name": "Khách hàng minh họa", "finance_id": None, "status": "calculated", "reasons": [],
             "below": number(below), "above": number(above), "gross_profit": "4000000",
             "revenue": "12000000", "floor": "10000000", "cost": "8000000", "receipt_total": "12000000",
             "is_example": True, "ready_at": None}]


def report(rows, method, selected_fund, page):
    valid = [r for r in rows if r["status"] == "calculated"]
    with localcontext() as ctx:
        ctx.prec = 50
        below = sum((Decimal(r["below"]) for r in valid), ZERO)
        above = sum((Decimal(r["above"]) for r in valid), ZERO)
        funds = allocate(below, above)
        detail = allocation_index(funds).get(selected_fund)
        if selected_fund and detail is None:
            raise ValidationError("Không tìm thấy quỹ trong bảng CAVI.")
        selected = valid if detail else rows
        page_rows = selected[(page - 1) * 20:page * 20]
        if detail:
            page_rows = [{**r, "allocation": allocation_index(allocate(Decimal(r["below"]), Decimal(r["above"])))[selected_fund]}
                         for r in page_rows]
        return {"funds": funds, "detail": detail, "total": number(below + above),
                "below": number(below), "above": number(above), "order_count": len(rows),
                "calculated_count": len(valid), "waiting_count": len(rows) - len(valid),
                "rows": {"count": len(selected), "page": page, "page_size": 20, "results": page_rows}}


class Funds(PrivateView):
    @transaction.atomic
    def get(self, request):
        company = get_active_company(request)
        if company.code != "CAVI":
            raise ValidationError("Bảng tỷ lệ anh gửi chỉ dành cho CAVI; chưa áp sang công ty khác.")
        method = request.query_params.get("method", "floor")
        if method not in METHODS:
            raise ValidationError("Cách tách lợi nhuận không hợp lệ.")
        period = request.query_params.get("period", timezone.localdate().strftime("%Y-%m"))
        start, end = period_bounds(period)
        sample = request.query_params.get("example", "0")
        if sample not in {"0", "1"}:
            raise ValidationError("Chế độ minh họa không hợp lệ.")
        if sample == "1":
            rows = example_projection(method)
        else:
            orders = Order.objects.filter(company=company).filter(
                Q(finance__completed_at__gte=start, finance__completed_at__lt=end)
                | Q(finance__completed_at__isnull=True, created_at__gte=start, created_at__lt=end)
            ).select_related("company", "customer", "finance").prefetch_related(
                "items", "finance__costs", "finance__payments").order_by("-created_at", "-id")
            if orders.count() > MAX_ORDERS:
                raise ValidationError("Kỳ vượt 2.000 đơn của bản TEST; cần xử lý tổng hợp riêng, không trả số tổng bị cắt thiếu.")
            rows = [order_projection(o, method) for o in orders]
        result = report(rows, method, request.query_params.get("fund", ""), page_number(request))
        return Response({**result, "company": {"id": company.pk, "code": company.code},
                         "period": period, "is_example": sample == "1", "policy": policy_info(method),
                         "updated_at": timezone.now().isoformat(), "posted": False, "cash_balance": None,
                         "period_note": "Lọc theo tháng hoàn thành. Đơn chưa hoàn thành dùng tháng tạo để hiển thị việc còn chờ. Chưa phải kỳ ghi sổ quỹ đã duyệt."})
