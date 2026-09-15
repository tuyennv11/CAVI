"""Read-only TEST fund projections. Never a cash balance or a payment ledger.

Rates: owner's CAVI allocation screenshot, received 2026-09-14.
Definition: Khái niệm, AVI-KD-NVKD0105 (01/05/2025), not yet confirmed for CAVI.
Keep the historic 75/25 calculation as an explicitly selected comparison only.
"""
from decimal import Decimal, localcontext

ZERO = Decimal("0")
POLICY_VERSION = "cavi-photo-2026-09-14-draft-v1"
DEFINITION_URL = "https://docs.google.com/document/d/1Q23Hf-Xe4llGd8fvMtFwOzbwX2P67xgF/edit"
HISTORY_URL = "https://docs.google.com/spreadsheets/d/1RQt-DI_p5bi3Tj3EfLSQhU4m9Lnh-mFf/edit"


def node(key, label, below, above, children=(), *, reserve=False):
    return {"key": key, "label": label, "below_pct": Decimal(below),
            "above_pct": Decimal(above), "children": children, "reserve": reserve}


# Parent rows are summaries, NEVER additional allocations.
FUNDS = (
    node("sales", "Bộ phận Kinh doanh", "20", "53", (
        node("sales_director", "Chi phí Giám đốc Kinh doanh", "1.5", "1.95"),
        node("sales_manager", "Chi phí Trưởng phòng Kinh doanh", "1.5", "1.95"),
        node("marketing_commission", "Chi phí Hoa hồng Marketing", "2", "8"),
        node("sales_commission", "Chi phí Hoa hồng Kinh doanh", "8", "32", (
            node("customer_work", "Làm việc Khách hàng", "5.5", "22"),
            node("sales_admin", "Sales Admin", "2.5", "10", (
                node("sales_assistant", "Trợ lý Kinh doanh", "1.5", "6"),
                node("data_entry", "Nhập liệu Phần mềm", "1", "4"),
            )),
        )),
        node("sales_reserve", "Nhập quỹ Kinh doanh", "7", "9.1", reserve=True),
    )),
    node("supply", "Bộ phận Cung ứng", "10", "4", (
        node("supply_director", "Chi phí Giám đốc Cung ứng", "1", ".4"),
        node("supply_manager", "Chi phí Trưởng phòng Cung ứng", "1", ".4"),
        node("purchasing_commission", "Chi phí Hoa hồng Thu mua", "5", "2"),
        node("supply_reserve", "Nhập quỹ Cung ứng", "3", "1.2", reserve=True),
    )),
    node("operations", "Bộ phận Vận hành", "8", "3.2", (
        node("operations_director", "Chi phí Giám đốc Vận hành", "1", ".4"),
        node("operations_manager", "Chi phí Trưởng phòng Vận hành", "1", ".4"),
        node("operations_staff", "Chi phí Nhân viên Vận hành", "3", "1.2"),
        node("operations_reserve", "Nhập quỹ Vận hành", "3", "1.2", reserve=True),
    )),
    node("warehouses", "Các Kho", "15", "6"),
    node("director", "Quỹ Giám đốc", "3", "1.2"),
    node("treasury", "Bộ phận Thủ quỹ", "2", ".8"),
    node("accounting", "Bộ phận Tài chính - Kế toán", "3", "1.2"),
    node("research", "Bộ phận R&D", "3", "1.2"),
    node("legal", "Bộ phận Pháp chế", "2", ".8"),
    node("hr", "Bộ phận Hành chính Nhân sự", "2", ".8"),
    node("office", "Quỹ Văn phòng", "3", "1.2"),
    node("unallocated", "Quỹ Chờ phân bổ", "4", "1.6"),
    node("shareholders", "Quỹ Cổ đông", "25", "25"),
)
METHODS = {"floor": "Theo giá sàn từng đơn (định nghĩa nguồn)",
           "historical_75_25": "So sánh cách chia cố định 75% / 25%"}


def number(value):
    """Plain exact decimal JSON, no float or implicit monetary rounding."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def validate_policy(nodes=FUNDS, below=Decimal(100), above=Decimal(100)):
    for field, expected in (("below_pct", below), ("above_pct", above)):
        if sum((item[field] for item in nodes), ZERO) != expected:
            raise ValueError("Tỷ lệ phân bổ không khớp dòng tổng.")
    for item in nodes:
        if item["below_pct"] < 0 or item["above_pct"] < 0:
            raise ValueError("Tỷ lệ phân bổ không được âm.")
        if item["children"]:
            validate_policy(item["children"], item["below_pct"], item["above_pct"])


def profit_bands(revenue, floor, cost, method="floor"):
    if method not in METHODS:
        raise ValueError("Cách tách lợi nhuận không hợp lệ.")
    with localcontext() as ctx:
        ctx.prec = 50
        total = revenue - cost
        below = floor - cost if method == "floor" else total * Decimal(".75")
        return below, total - below


def allocate(below, above, nodes=FUNDS):
    """Exact projections; callers hold negative bands for review, never clamp them."""
    with localcontext() as ctx:
        ctx.prec = 50
        result = []
        for item in nodes:
            low = below * item["below_pct"] / 100
            high = above * item["above_pct"] / 100
            children = allocate(below, above, item["children"])
            result.append({"key": item["key"], "label": item["label"],
                           "below_pct": number(item["below_pct"]), "above_pct": number(item["above_pct"]),
                           "below_amount": number(low), "above_amount": number(high),
                           "amount": number(low + high), "reserve": item["reserve"], "children": children})
        return result


def allocation_index(nodes):
    result = {}
    for item in nodes:
        result[item["key"]] = item
        result.update(allocation_index(item["children"]))
    return result


def policy_info(method):
    return {"version": POLICY_VERSION, "status": "needs_confirmation", "method": method,
            "method_label": METHODS[method], "methods": METHODS,
            "warning": "Dự tính TEST, chưa phải số dư được phép chi. Cần xác nhận định nghĩa áp dụng cho CAVI, ngày hiệu lực, kỳ ghi quỹ và cách xử lý đơn lỗ/hoàn tiền.",
            "sources": [
                {"label": "Bảng PHÂN BỔ QUỸ BỘ PHẬN CAVI anh gửi ngày 14/09/2026", "note": "Tỷ lệ hai cột đều cộng đủ 100%; dòng con nằm trong dòng tổng."},
                {"label": "Khái niệm · AVI-KD-NVKD0105 · 01/05/2025", "url": DEFINITION_URL,
                 "note": "Đã đọc: đơn thực hiện, thu đủ công nợ. Văn bản mang mã AVI; chưa tự coi là chính sách CAVI đã duyệt."},
                {"label": "Chia quỹ sales - cung ứng T2/2026", "url": HISTORY_URL,
                 "note": "Các dòng đã đối chiếu có cơ sở chia 75%/25%; không đủ chứng minh đây là quy tắc hiện hành."},
            ],
            "formulas": ["Lợi nhuận gộp = tiền dịch vụ đã thực thu − giá vốn − chi phí bán hàng",
                         "Lợi nhuận dưới sàn = doanh thu theo giá sàn − giá vốn − chi phí bán hàng",
                         "Lợi nhuận trên sàn = lợi nhuận gộp − lợi nhuận dưới sàn",
                         "Khoản phân bổ = lợi nhuận dưới sàn × tỷ lệ cột ≤ sàn + lợi nhuận trên sàn × tỷ lệ cột > sàn"],
            "limits": ["Không tính COD thu hộ là doanh thu dịch vụ. Chỉ đối chiếu VND cùng tiền tệ; không tự đoán tỷ giá.",
                       "Chi phí = giá vốn dòng hàng + chi phí bổ sung đã nhập. Chưa tự sinh lãi công nợ, chiết khấu hoặc chi phí chưa khai báo.",
                       "Giữ nguyên số âm để đối chiếu; chưa trừ vào quỹ hay chia tiền từ đơn có phần lợi nhuận âm.",
                       "Tổng bộ phận bao gồm chi phí/hoa hồng và Nhập quỹ; không coi cả tổng là tiền nhập quỹ còn lại.",
                       "Không làm tròn số tính. Màn hình hiển thị tối đa 4 số lẻ; chưa có quy tắc làm tròn khi chi.",
                       "Quy định trần chi nhân sự 80% là bước khác, không nhân 80% vào bảng hình thành quỹ này."]}


validate_policy()
