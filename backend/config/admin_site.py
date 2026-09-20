"""Sắp xếp lại trang quản trị (admin) theo đúng luồng nghiệp vụ thực tế, thay vì để Django tự xếp
theo alphabet (sẽ ngày càng lộn xộn khi có thêm app/model). Trình tự phản ánh đúng cách công ty vận
hành: có Nhân sự trước -> tạo Tài khoản cho nhân sự -> Nhân sự làm việc với Đối tác -> Đối tác tương
tác/hỏi giá -> Kinh doanh báo giá -> Khách chốt thành Đơn hàng -> Vận hành xử lý -> Kế toán thu chi/
công nợ. Dữ liệu tra cứu hành chính (Quốc gia/Tỉnh/Huyện/Xã) không thuộc luồng nghiệp vụ nào nên đặt
cuối cùng, chỉ dùng để chọn khi nhập địa chỉ ở nơi khác.

App/model không được liệt kê ở APP_ORDER/MODEL_ORDER vẫn hiện bình thường, chỉ tự rơi xuống cuối danh
sách tương ứng theo thứ tự chữ cái — không bị lỗi hay mất tích.
"""

from django.contrib import admin
from django.urls import reverse

APP_ORDER = ["companies", "hr", "auth", "crm", "inventory", "ops", "approvals", "geo"]

MODEL_ORDER = {
    # Hồ sơ nhân sự trước, Chức vụ/Bộ phận/Phòng là danh mục tra cứu, Nhật ký thay đổi cuối cùng (ít
    # khi cần mở trực tiếp, chỉ để tra cứu khi cần).
    "hr": ["Profile", "Position", "Department", "Room", "ProfileChangeLog"],
    # Kho trước, Hàng hoá sau (hàng hoá cần chọn kho lúc nhập), Nhật ký nhập-xuất cuối (tra cứu).
    "inventory": ["Warehouse", "Product", "StockMovement"],
    # Tài khoản đăng nhập trước, Nhóm quyền sau (gán nhóm cho tài khoản, không phải ngược lại).
    "auth": ["User", "Group"],
    "crm": [
        "Partner",  # Đối tác — điểm chạm đầu tiên với bên ngoài
        "Activity",  # Tương tác khách hàng — lưu lại mọi lần liên hệ
        "PriceInquiry",  # Khách hỏi giá — Kinh doanh + Cung ứng phối hợp báo giá vốn
        "PriceListItem",  # Bảng giá dịch vụ — dữ liệu dùng để cấu thành giá trong Hỏi giá/Báo giá
        "PriceInquiryQuoteLine",  # Dòng dịch vụ cấu thành của 1 Hỏi giá
        "PriceInquiryQuoteLineBid",  # Sàn báo giá cạnh tranh — nhiều Cung ứng chào giá cho 1 dòng
        "Quotation",  # Kinh doanh chốt báo giá gửi khách
        "Order",  # Khách chốt -> thành Phiếu nhận hàng/Đơn hàng chính thức
        "TierUpgradeRequest",  # Phát sinh từ quan hệ với Đối tác — phụ, không phải luồng chính
        "Task",  # Công việc nội bộ hỗ trợ
        "KPITarget",  # Quản lý nội bộ
        "Notice",  # Thông báo chung — ít ưu tiên nhất
    ],
    # Kiện hàng phát sinh trước (vận hành xử lý từng đơn), gom nhiều kiện lại thành 1 Chuyến sau.
    "ops": ["Shipment", "ShipmentBatch"],
    # Tra cứu hành chính — theo đúng cấp bậc Quốc gia -> Tỉnh -> Huyện -> Xã.
    "geo": ["Country", "Province", "District", "Ward"],
}


def _model_sort_key(order_list):
    def key(model):
        name = model["object_name"]
        return (order_list.index(name) if name in order_list else len(order_list), name)

    return key


def _app_sort_key(app):
    label = app["app_label"]
    return (APP_ORDER.index(label) if label in APP_ORDER else len(APP_ORDER), label)


_original_get_app_list = admin.AdminSite.get_app_list


def _get_app_list_by_workflow(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label=app_label)
    app_list.sort(key=_app_sort_key)
    for app in app_list:
        order_list = MODEL_ORDER.get(app["app_label"])
        if order_list:
            app["models"].sort(key=_model_sort_key(order_list))
    return app_list


admin.AdminSite.get_app_list = _get_app_list_by_workflow


# Thanh "sheet" cố định dưới cùng, giống thanh tab của Excel — mỗi model 1 tab, bấm vào là nhảy
# thẳng tới danh sách dữ liệu của model đó (không phải mở lại menu/sidebar từng cấp như trước). Dùng
# lại đúng get_app_list() đã lọc quyền + sắp xếp theo luồng nghiệp vụ ở trên, nên 1 người chỉ thấy
# tab của model họ có quyền xem, đúng thứ tự APP_ORDER/MODEL_ORDER — không cần khai báo trùng 1 danh
# sách riêng ở đây rồi bị lệch với sidebar khi sau này thêm/bớt model.
_original_each_context = admin.AdminSite.each_context


def _each_context_with_tabs(self, request):
    context = _original_each_context(self, request)
    tabs = [{"label": "Mục lục", "url": reverse("admin:index")}]
    if request.user.is_active:
        for app in self.get_app_list(request):
            for model in app["models"]:
                url = model.get("admin_url")
                if url:
                    tabs.append({"label": model["name"], "url": url})
    context["excel_tabs"] = tabs
    return context


admin.AdminSite.each_context = _each_context_with_tabs


# Trang chủ /admin/ hiển thị 1 bảng phẳng duy nhất (Tên bảng | Nhóm | Số dòng), giống hệt sheet "Mục
# lục" trong file Excel xuất từ database — cùng 1 nguồn dữ liệu (get_app_list đã lọc quyền + sắp xếp
# theo luồng nghiệp vụ ở trên), chỉ khác định dạng hiển thị. Chỉ tính .count() ở đúng trang này (không
# phải trong each_context — chạy trên mọi trang admin sẽ tốn không cần thiết).
_original_index = admin.AdminSite.index


def _index_with_excel_rows(self, request, extra_context=None):
    extra_context = extra_context or {}
    rows = []
    if request.user.is_active:
        for app in self.get_app_list(request):
            for model in app["models"]:
                url = model.get("admin_url")
                if not url:
                    continue
                try:
                    count = model["model"]._default_manager.count()
                except Exception:
                    count = None
                rows.append({"label": model["name"], "group": app["name"], "url": url, "count": count})
    extra_context["excel_index_rows"] = rows
    return _original_index(self, request, extra_context=extra_context)


admin.AdminSite.index = _index_with_excel_rows
