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

APP_ORDER = ["companies", "hr", "auth", "crm", "inventory", "ops", "approvals", "geo"]

MODEL_ORDER = {
    # Hồ sơ nhân viên trước, rồi tới Lương/Thưởng-phạt, Chấm công/Phép, Nhật ký thay đổi cuối cùng
    # (ít khi cần mở trực tiếp, chỉ để tra cứu khi cần).
    "hr": ["Profile", "CompensationRecord", "BonusPenaltyRecord", "AttendanceRecord", "LeaveBalance", "ProfileChangeLog"],
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
