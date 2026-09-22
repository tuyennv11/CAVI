from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from companies.models import Company
from companies.utils import get_default_company_id
from geo.models import Country, District, Province, Ward
from inventory.models import Product, Warehouse


class Partner(models.Model):
    class Tier(models.TextChoices):
        STANDARD = "standard", "Thường"
        VIP = "vip", "VIP"
        SUPER_VIP = "super_vip", "Siêu VIP"

    class Status(models.TextChoices):
        ACTIVE = "dang_hoat_dong", "Đang hoạt động"
        PAUSED = "tam_ngung", "Tạm ngừng"
        STOPPED = "ngung_hop_tac", "Ngừng hợp tác"

    # Mã đối tác tự sinh 1 lần lúc tạo (xem save()) — không cho sửa tay.
    code = models.CharField("Id đối tác", max_length=20, unique=True, blank=True, editable=False)
    # 2 cờ độc lập thay vì 1 field "Loại đối tác" (khách hàng/nhà cung cấp/cả hai) — 1 đối tác có
    # thể vừa là khách hàng vừa là nhà cung cấp, đây là 2 sự thật độc lập, không phải 1 lựa chọn
    # duy nhất. Cách cũ buộc mọi chỗ lọc "ai là khách hàng" phải viết thêm điều kiện xử lý riêng
    # cho giá trị "cả hai" (dễ quên, dễ sót).
    is_customer = models.BooleanField("Là khách hàng", default=True)
    is_supplier = models.BooleanField("Là nhà cung cấp", default=False)
    name = models.CharField("Tên đối tác", max_length=255)
    contact_person = models.CharField("Người liên hệ", max_length=255, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    # Nhân sự phụ trách — liên kết thẳng tới Hồ sơ nhân sự (hr.Profile), KHÔNG phải Tài khoản đăng
    # nhập (User) như trước đây, để hiện đúng "Id nhân sự" (NS000001) thay vì tài khoản đăng nhập.
    # QUAN TRỌNG: field này còn dùng để PHÂN QUYỀN xem dữ liệu khắp hệ thống (crm/permissions.py,
    # crm/views.py, crm/workspace_views.py, ops/views.py, hr/views.py) — mọi nơi so sánh với
    # request.user PHẢI so với request.user.profile (không phải request.user thẳng) từ giờ trở đi.
    assigned_to = models.ForeignKey(
        "hr.Profile",
        verbose_name="Nhân sự phụ trách",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners",
    )
    note = models.TextField("Mô tả thêm", blank=True)
    # Xếp hạng gán tay — trước đây có thêm 1 lớp "Hạng tự động" tính theo thâm niên + doanh thu, kèm
    # luồng "Yêu cầu nâng hạng" (TierUpgradeRequest) để Quản lý duyệt; đã bỏ hẳn (anh yêu cầu, vì đã
    # có "Xếp hạng" gán tay này rồi, sẽ thiết kế lại hệ thống hạng tự động sau).
    tier_override = models.CharField(
        "Xếp hạng", max_length=20, choices=Tier.choices, null=True, blank=True
    )
    # Chỉ 1 ô địa chỉ tự do — khác với hr.Profile/Order (giữ cấu trúc Quốc gia/Tỉnh/Quận/Phường vì
    # cần cho tính giá gửi hàng theo khu vực), địa chỉ của Đối tác chỉ mang tính tham khảo/liên hệ,
    # không dùng để tính giá (điểm lấy/giao hàng thực tế của từng đơn đã có riêng ở Order), nên
    # không cần chuẩn hoá tới cấp Phường/Xã.
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # Đối tác dùng 1 hồ sơ chung, nhưng chỉ hiển thị/giao dịch được ở đúng những công ty đã tick —
    # 1 đối tác có thể thuộc 1 công ty, hoặc nhiều công ty cùng lúc (vd vừa CAVI vừa LIVI).
    companies = models.ManyToManyField(Company, verbose_name="Công ty", related_name="partners", blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Đối tác"
        verbose_name_plural = "Đối tác"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            last = Partner.objects.exclude(pk=self.pk).order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            while Partner.objects.filter(code=f"DT{next_number:010d}").exists():
                next_number += 1
            self.code = f"DT{next_number:010d}"
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        # 2 trạng thái đầu là giai đoạn "Phiếu nhận hàng" — Kinh doanh tạo phiếu với thông số dự kiến
        # (như báo giá đã chốt), Vận hành ghi nhận số liệu thực tế lúc nhận hàng (có thể lệch dự kiến,
        # vd báo 500kg nhận thực tế 480kg), rồi Kinh doanh xác nhận lại số liệu đó mới chính thức thành
        # "Đơn hàng" (chuyển sang NEW, vào pipeline vận hành đơn bình thường).
        PENDING_RECEIPT = "pending_receipt", "Chờ vận hành nhận hàng"
        PENDING_CONFIRMATION = "pending_confirmation", "Chờ Kinh doanh xác nhận"
        NEW = "new", "Mới"
        PROCESSING = "processing", "Đang xử lý"
        DONE = "done", "Hoàn thành"
        CANCELLED = "cancelled", "Huỷ"

    customer = models.ForeignKey(Partner, verbose_name="Khách hàng", on_delete=models.CASCADE, related_name="orders")
    # Nullable tạm thời — backfill CAVI cho dữ liệu cũ ở migration, rồi chuyển NOT NULL (xem
    # migration liên quan). Đơn hàng luôn thuộc đúng 1 công ty, không như Partner (dùng chung).
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, default=get_default_company_id, related_name="orders")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # Đơn được tạo từ báo giá nào (nếu có) — để Vận hành/đối chiếu sau này biết đơn bắt nguồn từ đâu.
    source_quotation = models.ForeignKey(
        "Quotation", verbose_name="Báo giá gốc",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="orders_created"
    )
    # 3 field dưới đây phục vụ luồng Yêu cầu giá mới (crm.PriceRequest/PriceCalculation) — đều
    # nullable, KHÔNG đụng gì tới đơn hàng cũ/luồng vận chuyển hiện có (source_quotation ở trên vẫn
    # là đường nối cho luồng cũ, độc lập với 2 field mới này).
    source_price_request = models.ForeignKey(
        "PriceRequest", verbose_name="Yêu cầu giá gốc",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="orders_created"
    )
    source_price_calculation = models.ForeignKey(
        "PriceCalculation", verbose_name="Phiên bản tính giá gốc",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="orders_created"
    )
    warehouse = models.ForeignKey(
        Warehouse, verbose_name="Kho xuất", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.PENDING_RECEIPT)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Vận hành ghi nhận",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    received_at = models.DateTimeField("Thời điểm ghi nhận", null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Kinh doanh xác nhận",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField("Thời điểm xác nhận", null=True, blank=True)
    # Nội dung mô tả lô hàng cho Vận hành — giống hệt phần "Mô tả"/"Hình ảnh" bên Hỏi giá (Tên hàng,
    # Số lượng, Kích thước, Cân nặng, Hình thức vận chuyển, Điểm lấy/giao, Giá trị hàng hoá, Ghi chú),
    # chỉ bỏ phần giá — Vận hành cần biết đủ thông tin để xử lý lô hàng, không cần thấy giá bán/giá vốn.
    # Đơn tạo từ báo giá copy thẳng từ inquiry.description/image; đơn tạo tay thì Kinh doanh nhập trực tiếp.
    description = models.TextField("Mô tả lô hàng", blank=True)
    image = models.FileField("Hình ảnh", upload_to="orders/%Y/%m/", null=True, blank=True)
    note = models.CharField("Ghi chú", max_length=500, blank=True)
    paid = models.BooleanField("Đã thanh toán", default=False)
    on_platform = models.BooleanField("Qua sàn", default=False)
    # Phục vụ in bill dán lên kiện hàng (dạng Viettel Post/GHN/GHTK/DHL) — Vận hành điền khi nhận hàng.
    # Giữ nguyên dạng chữ tự do (đủ cho việc in nhãn) — cộng thêm Phường/Xã dạng tham chiếu chuẩn
    # riêng cho từng điểm, để sau này tính giá gửi hàng theo khu vực (không thay thế 2 field text này).
    pickup_point = models.CharField("Điểm lấy hàng", max_length=255, blank=True)
    pickup_ward = models.ForeignKey(
        Ward, verbose_name="Phường/Xã lấy hàng", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    delivery_point = models.CharField("Điểm giao hàng", max_length=255, blank=True)
    delivery_ward = models.ForeignKey(
        Ward, verbose_name="Phường/Xã giao hàng", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    weight_kg = models.DecimalField("Khối lượng (kg)", max_digits=10, decimal_places=2, null=True, blank=True)
    cod_amount = models.DecimalField("Thu hộ (COD)", max_digits=14, decimal_places=2, null=True, blank=True)
    # Snapshot giá sàn/trần từ Hỏi giá gốc lúc tạo đơn (nếu đơn tạo từ báo giá) — để Kinh doanh/Vận
    # hành đối chiếu doanh thu thực tế của đơn có nằm trong khoảng quy định hay không. Đơn tạo thủ
    # công (không qua báo giá) sẽ để trống, vì không có Hỏi giá gốc để xác định các thông số này.
    floor_pct = models.DecimalField("Tỷ lệ giá sàn (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    ceiling_pct = models.DecimalField("Tỷ lệ giá trần (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    floor_price = models.DecimalField("Giá sàn", max_digits=14, decimal_places=2, null=True, blank=True)
    ceiling_price = models.DecimalField("Giá trần", max_digits=14, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Phiếu nhận hàng / Đơn hàng"
        verbose_name_plural = "Phiếu nhận hàng / Đơn hàng"

    def __str__(self):
        return f"Đơn #{self.pk} — {self.customer}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    @property
    def gross_profit(self):
        return sum((item.line_profit for item in self.items.all()), start=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name="Phiếu nhận hàng", on_delete=models.CASCADE, related_name="items")
    # Chỉ có ở đơn hàng của công ty Thương mại — dòng hàng ứng với 1 Hàng hoá cụ thể trong kho, để
    # biết xuất kho đúng sản phẩm nào khi xác nhận đơn (xem OrderViewSet.confirm_received). Đơn hàng
    # Vận chuyển (CAVI) không có tồn kho nên field này luôn trống.
    product = models.ForeignKey(
        Product, verbose_name="Hàng hoá", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    description = models.CharField("Mô tả", max_length=255)
    # Số lượng dự kiến lúc tạo Phiếu nhận hàng — Vận hành ghi nhận thực tế vào actual_quantity, rồi
    # khi Kinh doanh xác nhận, actual_quantity được chốt lại thành quantity chính thức (xem
    # OrderViewSet.confirm_received). Trước khi xác nhận, quantity vẫn là số liệu dự kiến ban đầu.
    quantity = models.DecimalField("Số lượng", max_digits=10, decimal_places=2, default=1)
    actual_quantity = models.DecimalField(
        "Số lượng thực nhận", max_digits=10, decimal_places=2, null=True, blank=True
    )
    unit_price = models.DecimalField("Đơn giá bán", max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Giá vốn", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Dòng hàng"
        verbose_name_plural = "Dòng hàng"

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def line_profit(self):
        return self.quantity * (self.unit_price - self.unit_cost)


class Activity(models.Model):
    """Hoạt động đối tác — lịch sử tương tác/công việc/kinh doanh/chăm sóc theo dòng thời gian. Gắn
    với 1 Đối tác (Partner) nói chung, không riêng khách hàng — Partner có thể vừa là khách hàng vừa
    là nhà cung cấp (is_customer/is_supplier độc lập), nên hoạt động ở đây cũng áp dụng cho cả 2."""

    class ActivityType(models.TextChoices):
        # Tương tác
        CALL = "call", "Cuộc gọi"
        EMAIL = "email", "Email"
        MESSAGE = "message", "Tin nhắn"
        MEETING = "meeting", "Gặp mặt"
        NOTE = "note", "Ghi chú"
        # Công việc
        TASK = "task", "Công việc cần làm"
        FOLLOW_UP = "follow_up", "Việc cần theo dõi lại"
        APPOINTMENT = "appointment", "Lịch hẹn / cuộc họp"
        # Kinh doanh
        OPPORTUNITY = "opportunity", "Cơ hội kinh doanh"
        QUOTE = "quote", "Báo giá"
        ORDER = "order", "Đơn hàng"
        CONTRACT = "contract", "Hợp đồng"
        PAYMENT = "payment", "Thanh toán"
        # Chăm sóc khách hàng
        SUPPORT_REQUEST = "support_request", "Yêu cầu hỗ trợ"
        COMPLAINT = "complaint", "Khiếu nại"
        ISSUE_HANDLING = "issue_handling", "Xử lý sự cố"
        POST_SALE_CARE = "post_sale_care", "Chăm sóc sau bán hàng"

    # Loại nào mặc định "Đã hoàn thành" ngay khi ghi nhận (mang tính lịch sử) —
    # còn lại mặc định "Chưa xử lý" (mang tính công việc cần làm).
    HISTORICAL_TYPES = {
        ActivityType.CALL, ActivityType.EMAIL, ActivityType.MESSAGE,
        ActivityType.MEETING, ActivityType.NOTE,
    }

    class Status(models.TextChoices):
        NOT_PROCESSED = "not_processed", "Chưa xử lý"
        IN_PROGRESS = "in_progress", "Đang xử lý"
        DONE = "done", "Hoàn thành"
        CANCELLED = "cancelled", "Huỷ"

    # Thứ tự field khớp đúng thứ tự cột lúc xuất Excel (xem ExcelModelResource) — nhóm theo: đối
    # tượng (đối tác/công ty/loại/trạng thái/tiêu đề) -> thời điểm -> người liên quan -> nội dung chi
    # tiết -> nhóm theo dõi lại -> tham chiếu liên quan -> nhật ký tạo/sửa.
    customer = models.ForeignKey(Partner, verbose_name="Đối tác", on_delete=models.CASCADE, related_name="activities")
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, default=get_default_company_id, related_name="activities")
    activity_type = models.CharField("Loại hoạt động", max_length=20, choices=ActivityType.choices)
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.NOT_PROCESSED)
    title = models.CharField("Tiêu đề", max_length=255)
    activity_at = models.DateTimeField("Ngày giờ", default=timezone.now)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người thực hiện", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người phụ trách", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    contact_person = models.CharField("Người liên hệ", max_length=255, blank=True)
    content = models.TextField("Nội dung", blank=True)
    result = models.TextField("Kết quả", blank=True)
    note = models.TextField("Ghi chú", blank=True)
    attachment = models.FileField("File đính kèm", upload_to="activities/%Y/%m/", null=True, blank=True)
    follow_up_date = models.DateField("Ngày cần theo dõi lại", null=True, blank=True)
    # Tuỳ chọn — vd khách hẹn "15h gọi lại" thì ghi rõ giờ, còn hẹn kiểu "thứ 4 tuần sau" thì để trống.
    follow_up_time = models.TimeField("Giờ hẹn nhắc", null=True, blank=True)
    # Tách riêng khỏi `status` — trạng thái hoạt động gốc (vd cuộc gọi đã "Hoàn thành") không
    # đồng nghĩa với việc đã nhắc/xử lý xong follow-up gắn với nó.
    follow_up_done = models.BooleanField("Đã nhắc việc cần theo dõi lại", default=False)
    related_order = models.ForeignKey(
        Order, verbose_name="Đơn hàng liên quan", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    related_reference = models.CharField(
        "Tham chiếu khác (báo giá/hợp đồng/cơ hội/phiếu hỗ trợ...)", max_length=255, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-activity_at"]
        verbose_name = "Hoạt động đối tác"
        verbose_name_plural = "Hoạt động đối tác"

    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.title}"


class PriceRequest(models.Model):
    """Yêu cầu giá — Kinh doanh tạo khi khách có nhu cầu, Cung ứng kiểm tra nguồn hàng/mua hàng rồi
    Price tính giá theo quy trình riêng (xem crm.PriceCalculation). KHÔNG gắn cứng với 1 lần mua hàng
    — 1 Yêu cầu giá có thể dùng chung 1 Đề nghị mua (crm.PurchaseRequest) với yêu cầu khác, xem
    crm.PurchaseRequestAllocation."""

    class Status(models.TextChoices):
        CHO_CUNG_UNG = "cho_cung_ung", "Chờ Cung ứng"
        DA_KIEM_TRA_NGUON_HANG = "da_kiem_tra_nguon_hang", "Đã kiểm tra nguồn hàng"
        CHO_TINH_GIA = "cho_tinh_gia", "Chờ tính giá"
        CHO_DUYET = "cho_duyet", "Chờ duyệt giá"
        DA_DUYET = "da_duyet", "Đã duyệt giá"
        DA_GUI_KHACH = "da_gui_khach", "Đã gửi khách"
        KHACH_DONG_Y = "khach_dong_y", "Khách đồng ý"
        KHACH_TU_CHOI = "khach_tu_choi", "Khách từ chối"
        DANG_THUONG_LUONG = "dang_thuong_luong", "Đang thương lượng"
        HUY = "huy", "Huỷ"

    # Khai tường minh để đổi verbose_name cột "id" mặc định ("ID") — export Excel/Admin list chỉ
    # hiện đúng 1 cột id là số nội bộ này, nhãn "Id yêu cầu giá" (không hiện cột "code" nữa, xem
    # PriceRequestResource.Meta.exclude).
    id = models.AutoField("Id yêu cầu giá", primary_key=True)
    # Mã yêu cầu giá tự sinh 1 lần lúc tạo (xem save()) — không cho sửa tay.
    code = models.CharField("Id yêu cầu giá", max_length=20, unique=True, blank=True, editable=False)
    customer = models.ForeignKey(
        Partner, verbose_name="Khách hàng", on_delete=models.CASCADE, related_name="price_requests"
    )
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, default=get_default_company_id, related_name="price_requests")
    # Nhân sự phụ trách — cùng kiểu FK hr.Profile với Partner.assigned_to (không phải Tài khoản đăng nhập).
    assigned_to = models.ForeignKey(
        "hr.Profile", verbose_name="Nhân sự phụ trách", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="price_requests"
    )
    # Điểm giao hàng — cùng cấu trúc Quốc gia/Tỉnh/Quận/Phường/Số nhà với hr.Profile (chuẩn hoá được
    # tới cấp Phường/Xã cho Việt Nam; Phường/Xã chưa có dữ liệu chuẩn cho nước khác thì để trống, ghi
    # chi tiết vào street_address). Không có "Điểm lấy hàng" — hỏi giá chỉ cần biết giao đến đâu, lấy
    # hàng ở đâu xử lý sau ở bước Đơn hàng (xem Order.pickup_point/pickup_ward).
    country = models.ForeignKey(
        Country, verbose_name="Quốc gia", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    province = models.ForeignKey(
        Province, verbose_name="Tỉnh/Thành phố", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    district = models.ForeignKey(
        District, verbose_name="Quận/Huyện", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    ward = models.ForeignKey(
        Ward, verbose_name="Phường/Xã", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    street_address = models.CharField("Số nhà, đường", max_length=255, blank=True)
    description = models.TextField("Mô tả", blank=True)
    status = models.CharField("Trạng thái", max_length=30, choices=Status.choices, default=Status.CHO_CUNG_UNG)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yêu cầu giá"
        verbose_name_plural = "Yêu cầu giá"

    def __str__(self):
        return f"Yêu cầu giá #{self.pk} — {self.customer}"

    def save(self, *args, **kwargs):
        if not self.code:
            last = PriceRequest.objects.exclude(pk=self.pk).order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            while PriceRequest.objects.filter(code=f"HG{next_number:06d}").exists():
                next_number += 1
            self.code = f"HG{next_number:06d}"
        super().save(*args, **kwargs)


class PriceRequestItem(models.Model):
    """1 dòng sản phẩm trong 1 Yêu cầu giá — 1 Yêu cầu giá có thể có nhiều sản phẩm (không gắn cứng
    1 yêu cầu = 1 hàng)."""

    class SourceStatus(models.TextChoices):
        CHUA_XAC_DINH = "chua_xac_dinh", "Chưa xác định"
        TON_KHO = "ton_kho", "Tồn kho"
        MUA_MOI = "mua_moi", "Mua mới"
        TON_KHO_VA_MUA_BO_SUNG = "ton_kho_va_mua_bo_sung", "Tồn kho + mua bổ sung"

    price_request = models.ForeignKey(PriceRequest, verbose_name="Yêu cầu giá", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, verbose_name="Hàng hoá", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    item_name = models.CharField("Tên hàng", max_length=255, blank=True)
    image = models.FileField("Hình ảnh sản phẩm", upload_to="price_requests/%Y/%m/", null=True, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField("Đơn vị", max_length=50, blank=True)
    # NguonHang — hệ thống tự tính (xem crm/services/price_request.py:refresh_source_status),
    # KHÔNG cho nhập tay.
    source_status = models.CharField(
        "Nguồn hàng", max_length=30, choices=SourceStatus.choices,
        default=SourceStatus.CHUA_XAC_DINH, editable=False,
    )
    # Cung ứng ước lượng nhanh trước khi có báo giá NCC thật (trên Sàn báo giá NCC) — để Kinh doanh
    # thấy sơ bộ giá trong lúc chờ, KHÔNG phải giá vốn chính thức (giá thật lấy từ SupplierQuote đã
    # chọn hoặc PriceCalculation sau này). Chỉ Cung ứng/Quản lý được sửa (xem PriceRequestItemViewSet).
    estimated_cost_price = models.DecimalField(
        "Giá vốn tạm tính", max_digits=14, decimal_places=2, null=True, blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng sản phẩm yêu cầu giá"
        verbose_name_plural = "Dòng sản phẩm yêu cầu giá"

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"


class CostQuote(models.Model):
    """Báo giá vốn — nằm giữa Yêu cầu giá và Sàn báo giá NCC (khác estimated_cost_price ở trên, vốn
    chỉ là 1 con số ước lượng nhanh). Nhiều dòng lịch sử cho 1 dòng Yêu cầu giá, không ghi đè, giống
    cách SupplierQuote/PriceCalculation đang làm. 1 câu trả lời có thể gồm nhiều mặt hàng (xem
    CostQuoteItem) — vd Cung ứng gộp chung 1 chuyến hàng cho nhiều sản phẩm cùng Yêu cầu giá, chỉ có
    1 điểm nhận hàng + 1 giá vận chuyển chung."""

    # Khai tường minh để đổi verbose_name cột "id" mặc định — cùng cách làm với PriceRequest.id.
    id = models.AutoField("Id trả lời yêu cầu giá", primary_key=True)
    price_request_item = models.ForeignKey(
        PriceRequestItem, verbose_name="Dòng yêu cầu giá", on_delete=models.CASCADE, related_name="cost_quotes"
    )
    # Điểm nhận hàng cho báo giá vốn này — cùng cấu trúc Quốc gia/Tỉnh/Quận/Phường/Số nhà với
    # PriceRequest, KHÔNG nhất thiết trùng địa chỉ giao hàng cho khách (đây là nơi Cung ứng dự tính
    # nhận hàng về trước khi giao tiếp).
    country = models.ForeignKey(
        Country, verbose_name="Quốc gia", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    province = models.ForeignKey(
        Province, verbose_name="Tỉnh/Thành phố", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    district = models.ForeignKey(
        District, verbose_name="Quận/Huyện", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    ward = models.ForeignKey(
        Ward, verbose_name="Phường/Xã", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    street_address = models.CharField("Số nhà, đường", max_length=255, blank=True)

    supplier_name = models.CharField("Nhà cung cấp", max_length=200, blank=True)
    carrier_name = models.CharField("Đơn vị vận chuyển", max_length=200, blank=True)
    confirmed = models.BooleanField("NCC đã xác nhận", default=False)
    valid_until = models.DateField("Hiệu lực đến", null=True, blank=True)
    available_at = models.DateField("Ngày có hàng", null=True, blank=True)
    tax_basis = models.CharField(max_length=20, default="unknown", choices=[("unknown", "Chưa rõ thuế"), ("included", "Đã gồm thuế"), ("excluded", "Chưa gồm thuế")])
    payment_terms = models.CharField(max_length=500, blank=True)
    delivery_terms = models.CharField(max_length=500, blank=True)
    delivery_snapshot = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    based_on = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="competing_quotes")
    supersedes = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="next_version")

    class ShippingRateBasis(models.TextChoices):
        KG = "kg", "kg"
        M3 = "m3", "m3"
        # 1 số NCC báo thẳng 1 số tiền trọn gói cho cả chuyến thay vì theo đơn giá/kg hoặc /m3 — chọn
        # basis này thì shipping_rate CHÍNH LÀ Tổng giá vốn vận chuyển luôn, không nhân với gì cả.
        TOTAL = "total", "Tổng cố định"

    # Giá cước vận chuyển nhập theo ĐƠN GIÁ (Cung ứng tự tra bên ngoài) — Tổng giá vốn vận chuyển
    # (property shipping_cost bên dưới) tự nhân với tổng trọng lượng hoặc tổng thể tích cộng dồn từ
    # mọi mặt hàng trong câu trả lời này, tuỳ chọn ở shipping_rate_basis (trừ basis TOTAL).
    shipping_rate = models.DecimalField("Giá cước vận chuyển", max_digits=14, decimal_places=2, null=True, blank=True)
    shipping_rate_basis = models.CharField(
        "Tính cước theo", max_length=10, choices=ShippingRateBasis.choices, default=ShippingRateBasis.KG,
    )
    note = models.TextField("Mô tả thêm", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Báo giá vốn"
        verbose_name_plural = "Báo giá vốn"

    def __str__(self):
        return f"Báo giá vốn — {self.price_request_item}"

    @property
    def shipping_cost(self):
        """Tổng giá vốn vận chuyển — tính tự động, không cho nhập tay trực tiếp (xem
        shipping_rate/shipping_rate_basis). NCC báo trọn gói (basis TOTAL) thì lấy thẳng
        shipping_rate; báo theo đơn giá/kg hoặc /m3 thì nhân với tổng trọng lượng/thể tích cộng dồn
        mọi mặt hàng trong câu trả lời này."""
        from .services.sourcing import freight_total
        return freight_total(self, self.shipping_rate, self.shipping_rate_basis)


class CostQuoteItem(models.Model):
    """1 dòng mặt hàng trong 1 câu Trả lời yêu cầu giá (CostQuote) — dòng đầu tiên thường lấy sẵn từ
    Dòng yêu cầu giá gốc (item_name/quantity/unit), Cung ứng có thể sửa và thêm nhiều dòng khác."""

    # Ngưỡng đổi đơn vị hiển thị Tổng trọng lượng: dưới ngưỡng hiện kg, từ ngưỡng trở lên hiện tấn.
    WEIGHT_DISPLAY_THRESHOLD_KG = 1000

    cost_quote = models.ForeignKey(CostQuote, verbose_name="Câu trả lời", on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField("Mặt hàng", max_length=255, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    unit_cost = models.DecimalField("Giá vốn đơn vị", max_digits=14, decimal_places=2, null=True, blank=True)
    # Kích thước/trọng lượng lưu cố định 1 đơn vị chuẩn (cm/kg) — ô nhập trên web cho chọn cm/m hoặc
    # kg/tấn để gõ thuận tay hơn, tự quy đổi về đây trước khi lưu (xem CostQuoteBoard.jsx).
    unit_length_cm = models.DecimalField("Dài (cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    unit_width_cm = models.DecimalField("Rộng (cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    unit_height_cm = models.DecimalField("Cao (cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    unit_weight_kg = models.DecimalField("Trọng lượng đơn vị (kg)", max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng mặt hàng trả lời yêu cầu giá"
        verbose_name_plural = "Dòng mặt hàng trả lời yêu cầu giá"

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    @property
    def total_cost(self):
        """Tổng giá vốn — luôn tính tự động (SL × Giá vốn đơn vị), không cho nhập tay."""
        if self.quantity is None or self.unit_cost is None:
            return None
        return self.quantity * self.unit_cost

    @property
    def total_volume_m3(self):
        """Tổng kích thước quy ra m3 — luôn tính tự động (Dài×Rộng×Cao đổi ra mét, nhân Số lượng)."""
        if None in (self.quantity, self.unit_length_cm, self.unit_width_cm, self.unit_height_cm):
            return None
        unit_m3 = (self.unit_length_cm / 100) * (self.unit_width_cm / 100) * (self.unit_height_cm / 100)
        return unit_m3 * self.quantity

    @property
    def total_weight_kg(self):
        """Tổng trọng lượng (kg) — luôn tính tự động (SL × Trọng lượng đơn vị)."""
        if self.quantity is None or self.unit_weight_kg is None:
            return None
        return self.quantity * self.unit_weight_kg


class PurchaseRequest(models.Model):
    """Đề nghị mua hàng — KHÔNG gắn cứng 1-1 với 1 Yêu cầu giá. Có thể phục vụ nhiều Yêu cầu giá cùng
    lúc (xem PurchaseRequestAllocation), hoặc không phục vụ khách nào cả (mua nhập kho bán dần)."""

    class PurchaseType(models.TextChoices):
        THEO_DON_KHACH = "theo_don_khach", "Mua theo nhu cầu khách"
        NHAP_KHO = "nhap_kho", "Mua nhập kho"

    code = models.CharField("Id đề nghị mua", max_length=20, unique=True, blank=True, editable=False)
    purchase_type = models.CharField("Loại mua", max_length=20, choices=PurchaseType.choices)
    # Chỉ có ý nghĩa với "Mua nhập kho" (chưa chắc gắn khách nào) — Kho nhận cho biết hàng về đâu.
    warehouse = models.ForeignKey(
        Warehouse, verbose_name="Kho nhận", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_requests"
    )
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Đề nghị mua hàng"
        verbose_name_plural = "Đề nghị mua hàng"

    def __str__(self):
        return f"{self.code} — {self.get_purchase_type_display()}"

    def save(self, *args, **kwargs):
        if not self.code:
            last = PurchaseRequest.objects.exclude(pk=self.pk).order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            while PurchaseRequest.objects.filter(code=f"DM{next_number:06d}").exists():
                next_number += 1
            self.code = f"DM{next_number:06d}"
        super().save(*args, **kwargs)


class PurchaseRequestItem(models.Model):
    """1 dòng sản phẩm cần mua trong 1 Đề nghị mua — hỗ trợ nhiều sản phẩm/đề nghị."""

    purchase_request = models.ForeignKey(
        PurchaseRequest, verbose_name="Đề nghị mua hàng", on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, verbose_name="Hàng hoá", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    item_name = models.CharField("Tên hàng", max_length=255, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2)
    unit = models.CharField("Đơn vị", max_length=50, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng đề nghị mua hàng"
        verbose_name_plural = "Dòng đề nghị mua hàng"

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"


class PurchaseRequestAllocation(models.Model):
    """Phân bổ 1 dòng Đề nghị mua cho 1 dòng Yêu cầu giá cụ thể — đúng nguyên tắc "1 đề nghị mua có
    thể phục vụ nhiều yêu cầu giá, 1 yêu cầu giá có thể dùng chung 1 đề nghị mua với người khác".
    `price_request_item` để trống nghĩa là phần đó dành cho tồn kho bán dần, không phục vụ riêng
    khách nào (vd mua 5.000, 1.000 cho khách A, 2.000 cho khách B, 2.000 còn lại vào kho)."""

    purchase_request_item = models.ForeignKey(
        PurchaseRequestItem, verbose_name="Dòng đề nghị mua", on_delete=models.CASCADE, related_name="allocations"
    )
    price_request_item = models.ForeignKey(
        PriceRequestItem, verbose_name="Dòng yêu cầu giá", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="purchase_allocations"
    )
    quantity_allocated = models.DecimalField("Số lượng phân bổ", max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        verbose_name = "Phân bổ đề nghị mua"
        verbose_name_plural = "Phân bổ đề nghị mua"

    def __str__(self):
        target = self.price_request_item or "Tồn kho"
        return f"{self.purchase_request_item} → {target}: {self.quantity_allocated}"


class SupplierQuote(models.Model):
    """Báo giá NCC cho 1 dòng Đề nghị mua — nhiều dòng lịch sử, KHÔNG ghi đè (mỗi báo giá mới là 1
    bản ghi riêng để giữ lịch sử so sánh)."""

    purchase_request_item = models.ForeignKey(
        PurchaseRequestItem, verbose_name="Dòng đề nghị mua", on_delete=models.CASCADE, related_name="supplier_quotes"
    )
    supplier = models.ForeignKey(
        Partner, verbose_name="Nhà cung cấp", on_delete=models.CASCADE, related_name="supplier_quotes"
    )
    unit_price = models.DecimalField("Giá mua", max_digits=14, decimal_places=2)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2)
    unit = models.CharField("Đơn vị", max_length=50, blank=True)
    pickup_point = models.CharField("Điểm lấy hàng", max_length=255, blank=True)
    total_packages = models.PositiveIntegerField("Tổng số kiện", null=True, blank=True)
    package_dimensions = models.CharField("Kích thước kiện", max_length=255, blank=True)
    total_cbm = models.DecimalField("Tổng CBM", max_digits=10, decimal_places=2, null=True, blank=True)
    total_weight_kg = models.DecimalField("Tổng trọng lượng (kg)", max_digits=10, decimal_places=2, null=True, blank=True)
    available_at = models.DateField("Thời gian có hàng", null=True, blank=True)
    payment_terms = models.CharField("Điều kiện thanh toán", max_length=255, blank=True)
    delivery_terms = models.CharField("Điều kiện giao nhận", max_length=255, blank=True)
    # Giá vận chuyển từ điểm nhận hàng NCC sang điểm nhận bên kia (VN<->Cam) — Cung ứng tự tra bên
    # ngoài rồi nhập tay, hệ thống không tự tính (không có bảng giá cước theo tuyến).
    shipping_cost = models.DecimalField("Giá vận chuyển", max_digits=14, decimal_places=2, null=True, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    # NCC được chọn làm nguồn mua chính cho dòng đề nghị mua này — không tự động đổi is_selected của
    # các báo giá khác, Cung ứng tự chọn tay đúng 1 cái (nghiệp vụ chỉ 1 NCC chính tại 1 thời điểm,
    # nhưng không ép ràng buộc unique ở DB để không chặn việc đổi ý giữa chừng).
    is_selected = models.BooleanField("Là nguồn mua chính", default=False)
    # Bắt buộc có nội dung khi Kinh doanh chọn 1 báo giá KHÔNG PHẢI rẻ nhất (validate ở action
    # select, xem SupplierQuoteViewSet) — để lại vết vì sao không chọn giá rẻ nhất.
    selection_note = models.TextField("Lý do chọn", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Báo giá nhà cung cấp"
        verbose_name_plural = "Báo giá nhà cung cấp"

    def __str__(self):
        return f"{self.supplier}: {self.unit_price}/{self.unit}"

    @property
    def landed_unit_cost(self):
        """Giá quy đổi trên 1 đơn vị, đã cộng giá vận chuyển — dùng để so sánh báo giá nào rẻ nhất
        khi các báo giá có giá vận chuyển khác nhau."""
        extra = (self.shipping_cost / self.quantity) if (self.shipping_cost and self.quantity) else 0
        return self.unit_price + extra


class PriceInquiryMessage(models.Model):
    """Trao đổi qua lại giữa Kinh doanh và Cung ứng trong một yêu cầu hỏi giá."""

    inquiry = models.ForeignKey(PriceRequest, verbose_name="Hỏi giá", on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người gửi", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    content = models.TextField("Nội dung")
    # Đánh dấu tin nhắn hệ thống tự sinh khi chốt giá, để hiển thị khác trong luồng trao đổi.
    is_quote = models.BooleanField("Là tin chốt giá", default=False)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Tin nhắn hỏi giá"
        verbose_name_plural = "Tin nhắn hỏi giá"

    def __str__(self):
        return f"{self.author} — {self.content[:40]}"


class PriceListItem(models.Model):
    """Bảng giá dịch vụ chuẩn — Cung ứng chọn từ đây khi lên chi tiết báo giá cho một Hỏi giá."""

    class Category(models.TextChoices):
        I = "I", "Loại I"
        II = "II", "Loại II"
        III = "III", "Loại III"

    # Chỉ công ty Vận chuyển (CAVI) dùng bảng này — thêm field cho đồng nhất với mọi bảng khác
    # (tránh phải xử lý đặc biệt 1 bảng duy nhất không có company ở mọi chỗ lọc theo công ty).
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.PROTECT, default=get_default_company_id, related_name="price_list_items")
    category = models.CharField("Phân loại", max_length=5, choices=Category.choices)
    group_name = models.CharField("Nhóm dịch vụ", max_length=255)
    group_code = models.CharField("Mã nhóm", max_length=10)
    item_code = models.CharField("Mã dịch vụ", max_length=20, unique=True)
    name = models.CharField("Tên dịch vụ", max_length=255)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    floor_pct = models.DecimalField("Giá sàn (%)", max_digits=6, decimal_places=2, default=0)
    ceiling_pct = models.DecimalField("Giá trần (%)", max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField("Đang sử dụng", default=True)

    class Meta:
        ordering = ["group_code", "item_code"]
        verbose_name = "Bảng giá dịch vụ"
        verbose_name_plural = "Bảng giá dịch vụ"

    def __str__(self):
        return f"{self.item_code} — {self.name}"


class PriceInquiryQuoteLine(models.Model):
    """Một dòng mặt hàng/dịch vụ trong báo giá chi tiết của một Hỏi giá — Cung ứng nhập sau khi trao đổi xong."""

    inquiry = models.ForeignKey(
        PriceRequest, verbose_name="Hỏi giá", on_delete=models.CASCADE, related_name="quote_lines"
    )
    item = models.ForeignKey(
        PriceListItem, verbose_name="Dịch vụ", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # `item` (dịch vụ vận chuyển) và `product` (hàng hoá thương mại) loại trừ nhau — đúng 1 trong 2,
    # tuỳ inquiry.company.business_type là Vận chuyển hay Thương mại (ép ở serializer validate()).
    product = models.ForeignKey(
        Product, verbose_name="Hàng hoá", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Snapshot lại tại thời điểm thêm dòng — bảng giá gốc có đổi sau này cũng không ảnh hưởng báo giá đã lập.
    item_name = models.CharField("Tên dịch vụ", max_length=255)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    floor_pct = models.DecimalField("Giá sàn (%)", max_digits=6, decimal_places=2, default=0)
    ceiling_pct = models.DecimalField("Giá trần (%)", max_digits=6, decimal_places=2, default=0)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, default=1)
    unit_cost = models.DecimalField("Đơn giá vốn", max_digits=14, decimal_places=2, default=0)
    note = models.TextField("Mô tả", blank=True)
    # Báo giá cạnh tranh (PriceInquiryQuoteLineBid) đã được Quản lý chọn làm giá chính thức cho dòng
    # này — khi chọn, `unit_cost` phía trên được đồng bộ luôn theo giá này (xem action "award" ở
    # views.py) để mọi công thức tính sẵn có (line_cost/line_floor/line_ceiling, confirm_quote) không
    # cần biết gì về khái niệm "đấu giá", chỉ đọc unit_cost như trước giờ.
    winning_bid = models.ForeignKey(
        "PriceInquiryQuoteLineBid", verbose_name="Báo giá thắng",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng dịch vụ cấu thành"
        verbose_name_plural = "Dòng dịch vụ cấu thành"

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    @property
    def line_cost(self):
        return self.quantity * self.unit_cost

    @property
    def line_floor(self):
        return self.line_cost * (1 + self.floor_pct / 100)

    @property
    def line_ceiling(self):
        return self.line_cost * (1 + self.ceiling_pct / 100)


class PriceInquiryQuoteLineBid(models.Model):
    """Báo giá cạnh tranh — Sàn báo giá: nhiều Cung ứng cùng chào giá vốn cho 1 dòng Dịch vụ cấu
    thành, tạo thành lịch sử để Quản lý so sánh rồi chọn 1 giá làm chính thức (xem
    PriceInquiryQuoteLine.winning_bid). Không cho sửa (PATCH) sau khi đã chào — người khác đã nhìn
    thấy giá đó rồi, muốn đổi thì xoá chào lại, giữ đúng tinh thần "sổ cái công khai"."""

    quote_line = models.ForeignKey(
        PriceInquiryQuoteLine, verbose_name="Dòng dịch vụ cấu thành", on_delete=models.CASCADE, related_name="bids"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người chào giá", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    unit_cost = models.DecimalField(
        "Đơn giá vốn chào", max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        # Đúng nghĩa "lịch sử" — sắp theo thời gian chào giá, KHÔNG sắp theo giá thấp/cao, để không
        # tự thiên vị giá rẻ khi hiển thị (Quản lý còn cần cân nhắc chất lượng dịch vụ, không chỉ giá).
        ordering = ["created_at"]
        verbose_name = "Báo giá cạnh tranh"
        verbose_name_plural = "Báo giá cạnh tranh"

    def __str__(self):
        return f"{self.quote_line.item_name}: {self.unit_cost} — {self.bidder}"


class PriceCalculation(models.Model):
    """Tính giá theo version cho 1 Yêu cầu giá — thay vai trò Quotation/QuotationLine cho luồng
    Yêu cầu giá mới (2 model đó GIỮ NGUYÊN, không đụng, chỉ không dùng cho bản ghi mới nữa). Mỗi lần
    tính lại giá (vd cước vận chuyển đổi) phải tạo version MỚI, không ghi đè version cũ — giữ đủ lịch
    sử "Version 1: 14,2 USD ... Version 2: 13,9 USD, giữ cả hai"."""

    class ApprovalStatus(models.TextChoices):
        CHO_DUYET = "cho_duyet", "Chờ duyệt"
        DA_DUYET = "da_duyet", "Đã duyệt"
        TU_CHOI = "tu_choi", "Từ chối"
        YEU_CAU_SUA = "yeu_cau_sua", "Yêu cầu sửa"

    price_request = models.ForeignKey(
        PriceRequest, verbose_name="Yêu cầu giá", on_delete=models.CASCADE, related_name="calculations"
    )
    # Tăng dần theo TỪNG price_request (không phải mã duy nhất toàn cục như `code` các model khác) —
    # version 1, 2, 3... của cùng 1 Yêu cầu giá.
    version = models.PositiveIntegerField("Phiên bản", editable=False)
    profit_pct = models.DecimalField("Tỷ lệ lợi nhuận (%)", max_digits=6, decimal_places=2, default=0)
    approval_status = models.CharField(
        "Trạng thái duyệt", max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.CHO_DUYET
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người duyệt", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["price_request_id", "version"]
        verbose_name = "Tính giá"
        verbose_name_plural = "Tính giá"

    def __str__(self):
        return f"{self.price_request} — v{self.version}"

    def save(self, *args, **kwargs):
        if not self.version:
            last = PriceCalculation.objects.filter(price_request=self.price_request).order_by("-version").first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)


class PriceCalculationItem(models.Model):
    """Chi tiết giá vốn/giá bán cho 1 dòng sản phẩm trong 1 phiên bản tính giá — đúng công thức
    Giá mua + Vận chuyển + Hải quan + Chi phí khác = Giá vốn."""

    price_calculation = models.ForeignKey(
        PriceCalculation, verbose_name="Tính giá", on_delete=models.CASCADE, related_name="items"
    )
    price_request_item = models.ForeignKey(
        PriceRequestItem, verbose_name="Dòng yêu cầu giá", on_delete=models.CASCADE, related_name="calculation_items"
    )
    purchase_cost = models.DecimalField("Giá mua", max_digits=16, decimal_places=2, default=0)
    transport_cost = models.DecimalField("Vận chuyển", max_digits=16, decimal_places=2, default=0)
    customs_cost = models.DecimalField("Hải quan", max_digits=16, decimal_places=2, default=0)
    other_cost = models.DecimalField("Chi phí khác", max_digits=16, decimal_places=2, default=0)
    proposed_price = models.DecimalField("Giá đề xuất", max_digits=16, decimal_places=2, default=0)
    final_price = models.DecimalField("Giá chốt", max_digits=16, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng tính giá"
        verbose_name_plural = "Dòng tính giá"

    def __str__(self):
        return f"{self.price_request_item.item_name}: {self.proposed_price}"

    @property
    def total_cost(self):
        return self.purchase_cost + self.transport_cost + self.customs_cost + self.other_cost


class Quotation(models.Model):
    """Báo giá chính thức gửi khách hàng — tạo từ 1 Hỏi giá đã chốt giá nội bộ, copy lại dữ liệu
    đã có (mô tả + các dòng dịch vụ) và cho chỉnh sửa tiếp trước khi gửi khách, độc lập với Hỏi giá gốc."""

    # 1 Hỏi giá có thể có nhiều báo giá đã lưu song song (vd nhiều phương án giá gửi khách) — mỗi cái
    # độc lập, Xuất PDF/Tạo đơn/Xoá riêng từng cái.
    inquiry = models.ForeignKey(PriceRequest, verbose_name="Hỏi giá", on_delete=models.CASCADE, related_name="quotations")
    note = models.TextField("Mô tả", blank=True)
    # Giá tổng báo giá phải nằm trong [giá sàn, giá trần] của Hỏi giá gốc mới lưu được trực tiếp —
    # nếu không, phải gửi đề xuất qua đây cho Cung ứng duyệt trước, duyệt xong mới lưu tiếp được.
    pending_approval = models.ForeignKey(
        "approvals.ApprovalRequest", verbose_name="Đề xuất đang chờ duyệt",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Snapshot nội dung (note + lines) đã gửi kèm đề xuất — không có chỗ nào khác lưu lại nội dung
    # đang chờ duyệt, nên trước đây sau khi gửi đề xuất rồi tải lại trang thì y như mất hết, chỉ còn
    # thấy bản đã lưu lần gần nhất. Giữ snapshot này để mở lại đúng nội dung đang chờ/đã duyệt.
    pending_snapshot = models.JSONField("Nội dung đề xuất đang chờ", null=True, blank=True)
    # Thời điểm bấm "Lưu báo giá" gần nhất — None nghĩa là báo giá vừa tạo, chưa từng lưu lần nào.
    # Không dùng updated_at != created_at để suy ra việc này được, vì auto_now/auto_now_add gọi
    # timezone.now() 2 lần riêng biệt ngay lúc tạo, nên gần như luôn khác nhau dù chưa ai bấm Lưu.
    saved_at = models.DateTimeField("Thời điểm lưu gần nhất", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Báo giá"
        verbose_name_plural = "Báo giá"

    def __str__(self):
        return f"Báo giá #{self.pk} — {self.inquiry.customer}"


class QuotationLine(models.Model):
    """Một dòng trong báo giá gửi khách — chỉ giữ những gì khách cần thấy (mô tả/ĐVT/SL/giá),
    bỏ hết chi tiết giá vốn/% nội bộ vì về sau chỉ cần quan tâm giá tổng của báo giá.
    `price` mặc định lấy từ giá sàn của dòng Hỏi giá gốc lúc tạo, sau đó chỉnh sửa độc lập."""

    quotation = models.ForeignKey(Quotation, verbose_name="Báo giá", on_delete=models.CASCADE, related_name="lines")
    # Giữ lại đường nối tới Hàng hoá — thiếu field này thì lúc tạo Đơn hàng từ Báo giá (xem
    # Quotation.create_order) sẽ mất dấu sản phẩm, không trừ được kho (xem PriceInquiryQuoteLine.product).
    product = models.ForeignKey(
        Product, verbose_name="Hàng hoá", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    item_name = models.CharField("Mô tả", max_length=255, blank=True)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, default=1)
    price = models.DecimalField("Giá", max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]
        verbose_name = "Dòng báo giá"
        verbose_name_plural = "Dòng báo giá"

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.price


class Task(models.Model):
    """Công việc — có thể tạo độc lập, từ một Hoạt động đối tác, hoặc từ Chat."""

    class Priority(models.TextChoices):
        LOW = "low", "Thấp"
        NORMAL = "normal", "Bình thường"
        HIGH = "high", "Cao"
        URGENT = "urgent", "Khẩn cấp"

    class Status(models.TextChoices):
        TODO = "todo", "Cần làm"
        IN_PROGRESS = "in_progress", "Đang làm"
        DONE = "done", "Hoàn thành"
        CANCELLED = "cancelled", "Huỷ"

    title = models.CharField("Tên công việc", max_length=255)
    content = models.TextField("Nội dung", blank=True)
    # Tuỳ chọn, giống hệt field `partner` — 1 công việc có thể không thuộc công ty cụ thể nào (vd
    # việc nội bộ chung cho cả 2 công ty).
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.SET_NULL, null=True, blank=True, default=get_default_company_id, related_name="tasks")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người phụ trách", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người giao", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    partner = models.ForeignKey(
        Partner, verbose_name="Khách hàng/đối tác liên quan", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks"
    )
    related_activity = models.ForeignKey(
        Activity, verbose_name="Hoạt động liên quan", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks"
    )
    due_at = models.DateTimeField("Hạn hoàn thành", null=True, blank=True)
    priority = models.CharField("Độ ưu tiên", max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.TODO)
    attachment = models.FileField("File liên quan", upload_to="tasks/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        ordering = ["due_at", "-created_at"]
        verbose_name = "Công việc"
        verbose_name_plural = "Công việc"

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return (
            bool(self.due_at)
            and self.due_at < timezone.now()
            and self.status not in (self.Status.DONE, self.Status.CANCELLED)
        )


class KPITarget(models.Model):
    """Chỉ tiêu KPI tháng của một nhân viên — hiện tại cấu hình qua trang Admin (do Quản lý đặt)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Nhân viên", on_delete=models.CASCADE, related_name="kpi_targets"
    )
    # Tuỳ chọn — tách chỉ tiêu theo từng công ty (đổi unique_together thành 4 cột) không nằm trong
    # yêu cầu hiện tại, để nullable, không mở rộng tính năng ngoài phạm vi.
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.SET_NULL, null=True, blank=True, default=get_default_company_id, related_name="kpi_targets")
    year = models.IntegerField("Năm")
    month = models.IntegerField("Tháng")
    revenue_target = models.DecimalField("Chỉ tiêu doanh thu", max_digits=16, decimal_places=2, default=0)
    new_customer_target = models.IntegerField("Chỉ tiêu khách hàng mới", default=0)
    quote_target = models.IntegerField("Chỉ tiêu báo giá", default=0)
    order_target = models.IntegerField("Chỉ tiêu đơn hàng", default=0)
    task_target = models.IntegerField("Chỉ tiêu công việc hoàn thành", default=0)

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ["user", "year", "month"]
        verbose_name = "Chỉ tiêu KPI"
        verbose_name_plural = "Chỉ tiêu KPI"

    def __str__(self):
        return f"KPI {self.user} — {self.month:02d}/{self.year}"


class Notice(models.Model):
    # Không set = thông báo cho TẤT CẢ công ty; set = thông báo riêng 1 công ty. Vì vậy để nullable
    # vĩnh viễn, không ép buộc — ép NOT NULL sẽ mất khả năng thông báo chung.
    company = models.ForeignKey(Company, verbose_name="Công ty", on_delete=models.SET_NULL, null=True, blank=True, default=get_default_company_id, related_name="notices")
    code = models.CharField("Số hiệu", max_length=50, blank=True)
    title = models.CharField("Tiêu đề", max_length=255)
    body = models.TextField("Nội dung", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người tạo", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Thông báo nội bộ"
        verbose_name_plural = "Thông báo nội bộ"

    def __str__(self):
        return self.title


class FreightOffer(models.Model):
    goods_quote = models.ForeignKey(CostQuote, on_delete=models.PROTECT, related_name="freight_offers")
    carrier_name = models.CharField(max_length=200)
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    basis = models.CharField(max_length=10, choices=CostQuote.ShippingRateBasis.choices, default="total")
    confirmed = models.BooleanField(default=False)
    valid_until = models.DateField(null=True, blank=True)
    delivery_days = models.PositiveIntegerField(null=True, blank=True)
    tax_basis = models.CharField(max_length=20, choices=[("unknown", "Chưa rõ thuế"), ("included", "Đã gồm thuế"), ("excluded", "Chưa gồm thuế")], default="unknown")
    terms = models.CharField(max_length=500, blank=True)
    delivery_snapshot = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    supersedes = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="next_version")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class SourcingPlan(models.Model):
    price_request_item = models.ForeignKey(PriceRequestItem, on_delete=models.PROTECT, related_name="sourcing_plans")
    goods_quote = models.ForeignKey(CostQuote, on_delete=models.PROTECT, related_name="sourcing_plans")
    freight_offer = models.ForeignKey(FreightOffer, on_delete=models.PROTECT, null=True, blank=True, related_name="sourcing_plans")
    status = models.CharField(max_length=20, default="proposed", choices=[("proposed", "Chờ duyệt"), ("approved", "Đã chốt"), ("rejected", "Không chọn")])
    reason = models.TextField()
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sourcing_proposals")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sourcing_reviews")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["price_request_item"], condition=models.Q(status="approved"), name="one_approved_sourcing_plan")]
