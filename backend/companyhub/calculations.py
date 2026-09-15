"""Explicit draft arithmetic only: no Excel eval, tax inference, approval or payment."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

FUND_REFERENCE = "CAVI-0511/QĐPB · 05/11/2025"
FUND_SOURCE_ID = "1N5oSISKz-XyscZylJm0Ff7ZtBYJqLzHH"
FUND_REVIEWED_DIGEST = "fe38c2bda0585ccf4caa4c98dbd5c347fcb6ce663022614e7328aa20b0d52348"
ELIGIBLE_DEPARTMENTS = {"operations", "accounting", "hr", "legal", "management", "marketing"}


def amount(value, label, *, positive=False):
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        raise ValueError(f"Chưa có {label}; không tự thay bằng 0.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} phải là số.") from None
    if not result.is_finite() or result < 0 or result > Decimal("1000000000000000"):
        raise ValueError(f"{label} không hợp lệ.")
    if positive and result <= 0:
        raise ValueError(f"{label} phải lớn hơn 0.")
    return result


def money(value):
    return str(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def unrounded_amount(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def fund_draft(data):
    if data.get("department") not in ELIGIBLE_DEPARTMENTS:
        raise ValueError("Quy định 80% không áp dụng cho Kinh doanh/Cung ứng; phải dùng chính sách riêng.")
    try:
        period = date.fromisoformat(data["period"] + "-01")
        previous = date.fromisoformat(data["fund_period"] + "-01")
    except (KeyError, TypeError, ValueError):
        raise ValueError("Cần kỳ đề xuất và kỳ quỹ theo dạng YYYY-MM.") from None
    expected = date(period.year - 1, 12, 1) if period.month == 1 else date(period.year, period.month - 1, 1)
    if previous != expected:
        raise ValueError("Quỹ phải thuộc tháng liền trước kỳ đề xuất.")
    if period < date(2025, 11, 1):
        raise ValueError("Kỳ nằm trước ngày văn bản có hiệu lực 05/11/2025.")
    keys = {"cavi_fund": "quỹ từ CAVI", "livi_fund": "quỹ từ LIVI", "service_fund": "quỹ dịch vụ tự cung cấp",
            "minimum_income": "thu nhập tối thiểu đã chi", "other_personnel_costs": "chi phí nhân sự khác", "proposed_bonus": "thưởng đề xuất"}
    values = {key: amount(data.get(key), label) for key, label in keys.items()}
    total = values["cavi_fund"] + values["livi_fund"] + values["service_fund"]
    ceiling = total * Decimal("0.8")
    spent = values["minimum_income"] + values["other_personnel_costs"]
    remaining = max(Decimal(0), ceiling - spent)
    excess = max(Decimal(0), spent + values["proposed_bonus"] - ceiling)
    return {"status": "draft", "reference": FUND_REFERENCE, "period": data["period"], "fund_period": data["fund_period"],
            "total_fund": money(total), "personnel_ceiling": money(ceiling), "already_spent": money(spent),
            "maximum_additional_bonus": money(remaining), "excess": money(excess), "within_ceiling": excess == 0,
            "approval_required": True, "payment_created": False,
            "trace": ["Tổng quỹ = CAVI + LIVI + dịch vụ tự cung cấp (tháng trước)",
                      "Trần chi nhân sự = tổng quỹ × 80%",
                      "Mức đề xuất thêm = tối đa(0, trần chi − thu nhập tối thiểu − chi phí nhân sự khác)"],
            "warning": "Bản tính nháp theo văn bản 05/11/2025, chưa xác nhận là chính sách mới nhất. Chưa duyệt, chưa chi tiền. Làm tròn hiển thị đến 1 đồng; kiểm tra trần bằng số chính xác."}


def payroll_components(cells, source_row):
    """Calculate only source-verified May components. Missing != zero, never output net pay."""
    results = []
    def value(column):
        item = cells.get(column, {})
        if item.get("error") or item.get("formula") and item.get("value") is None:
            raise ValueError(f"Ô {column} lỗi hoặc chưa có kết quả lưu từ nguồn.")
        return amount(item.get("value"), f"ô {column}", positive=column == "N")

    operations = [
        ("AF", "Lương cơ bản theo công", "I / N × S", lambda: value("I") / value("N") * value("S")),
        ("AN", "Phụ cấp chuyên cần", "J / N × S", lambda: value("J") / value("N") * value("S")),
        ("AO", "Hỗ trợ ăn ca", "K / N × S", lambda: value("K") / value("N") * value("S")),
        ("AQ", "Thưởng KPI", "L / N × S × AP", lambda: value("L") / value("N") * value("S") * value("AP")),
    ]
    for column, label, formula, operation in operations:
        try:
            r = int(source_row)
            expected = {"AF": f"=I{r}/N{r}*S{r}", "AN": f"=J{r}/N{r}*S{r}",
                        "AO": f"=K{r}/N{r}*S{r}", "AQ": f"=(L{r}/N{r}*S{r})*AP{r}"}
            original = str(cells.get(column, {}).get("formula", ""))
            if original != expected[column]:
                raise ValueError("Công thức dòng này khác mẫu đã kiểm chứng; cần đối chiếu riêng, không áp công thức chung.")
            calculated = operation()
            saved = cells.get(column, {}).get("value")
            comparable = isinstance(saved, (int, float)) and not isinstance(saved, bool)
            results.append({"column": column, "label": label, "formula": formula, "amount": unrounded_amount(calculated),
                            "source_amount": str(saved) if comparable else None,
                            "difference": unrounded_amount(calculated - Decimal(str(saved))) if comparable else None,
                            "status": "calculated"})
        except ValueError as error:
            results.append({"column": column, "label": label, "formula": formula, "amount": None, "status": "missing", "reason": str(error)})
    return {"status": "partial_draft", "components": results, "net_pay": None, "currency": None,
            "warning": "Chỉ đối chiếu 4 thành phần theo công thức tháng 05/2026. Giữ nguyên đơn vị số của dòng nguồn; chưa xác minh tiền tệ/làm tròn của từng người, không tự quy đổi VND. Chưa tính thuế, tăng ca, hoa hồng và thực lĩnh; không dùng để chốt lương kỳ mới."}
