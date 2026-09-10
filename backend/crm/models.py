from django.conf import settings
from django.db import models
from django.utils import timezone


class Partner(models.Model):
    class PartnerType(models.TextChoices):
        CUSTOMER = "customer", "Khách hàng"
        SUPPLIER = "supplier", "Nhà cung cấp"
        BOTH = "both", "Khách hàng - Nhà cung cấp"

    class Tier(models.TextChoices):
        STANDARD = "standard", "Thường"
        VIP = "vip", "VIP"
        SUPER_VIP = "super_vip", "Siêu VIP"

    name = models.CharField("Tên", max_length=255)
    contact_person = models.CharField("Người liên hệ", max_length=255, blank=True)
    phone = models.CharField("Số điện thoại", max_length=32, blank=True)
    note = models.TextField("Mô tả thêm", blank=True)
    partner_type = models.CharField(
        "Loại đối tác", max_length=20, choices=PartnerType.choices, default=PartnerType.CUSTOMER
    )
    # Hạng do hệ thống tự tính (xem computed_tier) — chỉ bị ghi đè khi có yêu cầu nâng hạng được duyệt.
    tier_override = models.CharField(
        "Hạng đã duyệt vượt bậc", max_length=20, choices=Tier.choices, null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Nhân viên phụ trách",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def tenure_months(self):
        delta = timezone.now() - self.created_at
        return delta.days // 30

    @property
    def total_revenue(self):
        orders = self.orders.exclude(status="cancelled").prefetch_related("items")
        return sum((o.total for o in orders), start=0)

    @property
    def computed_tier(self):
        months = self.tenure_months
        revenue = self.total_revenue
        if months >= settings.TIER_TENURE_MONTHS["super_vip"] and revenue >= settings.TIER_REVENUE_THRESHOLDS["super_vip"]:
            return self.Tier.SUPER_VIP
        if months >= settings.TIER_TENURE_MONTHS["vip"] and revenue >= settings.TIER_REVENUE_THRESHOLDS["vip"]:
            return self.Tier.VIP
        return self.Tier.STANDARD

    @property
    def tier(self):
        return self.tier_override or self.computed_tier

    @property
    def tier_source(self):
        return "approved" if self.tier_override else "auto"

    @property
    def credit_limit(self):
        return settings.TIER_CREDIT_LIMITS.get(self.tier, 0)

    @property
    def debt(self):
        if self.partner_type == self.PartnerType.SUPPLIER:
            return 0
        unpaid = self.orders.filter(paid=False).prefetch_related("items")
        return sum((o.total for o in unpaid), start=0)


class TierUpgradeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Đang chờ"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="tier_requests")
    requested_tier = models.CharField("Hạng xin lên", max_length=20, choices=Partner.Tier.choices)
    reason = models.TextField("Lý do")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.partner} → {self.get_requested_tier_display()} ({self.status})"


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Mới"
        PROCESSING = "processing", "Đang xử lý"
        DONE = "done", "Hoàn thành"
        CANCELLED = "cancelled", "Huỷ"

    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="orders")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # Đơn được tạo từ báo giá nào (nếu có) — để Vận hành/đối chiếu sau này biết đơn bắt nguồn từ đâu.
    source_quotation = models.ForeignKey(
        "Quotation", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders_created"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    note = models.CharField("Ghi chú", max_length=500, blank=True)
    paid = models.BooleanField("Đã thanh toán", default=False)
    on_platform = models.BooleanField("Qua sàn", default=False)
    # Phục vụ in bill dán lên kiện hàng (dạng Viettel Post/GHN/GHTK/DHL) — Vận hành điền khi nhận hàng.
    pickup_point = models.CharField("Điểm lấy hàng", max_length=255, blank=True)
    delivery_point = models.CharField("Điểm giao hàng", max_length=255, blank=True)
    weight_kg = models.DecimalField("Khối lượng (kg)", max_digits=10, decimal_places=2, null=True, blank=True)
    cod_amount = models.DecimalField("Thu hộ (COD)", max_digits=14, decimal_places=2, null=True, blank=True)
    # Snapshot giá sàn/trần từ Hỏi giá gốc lúc tạo đơn (nếu đơn tạo từ báo giá) — để Kinh doanh/Vận
    # hành đối chiếu doanh thu thực tế của đơn có nằm trong khoảng quy định hay không. Đơn tạo thủ
    # công (không qua báo giá) sẽ để trống, vì không có Hỏi giá gốc để xác định các thông số này.
    floor_pct = models.DecimalField("Tỷ lệ giá sàn (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    ceiling_pct = models.DecimalField("Tỷ lệ giá trần (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    floor_price = models.DecimalField("Giá sàn", max_digits=14, decimal_places=2, null=True, blank=True)
    ceiling_price = models.DecimalField("Giá trần", max_digits=14, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Đơn #{self.pk} — {self.customer}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    @property
    def gross_profit(self):
        return sum((item.line_profit for item in self.items.all()), start=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    description = models.CharField("Mô tả", max_length=255)
    quantity = models.DecimalField("Số lượng", max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField("Đơn giá bán", max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Giá vốn", max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def line_profit(self):
        return self.quantity * (self.unit_price - self.unit_cost)


class Activity(models.Model):
    """Hoạt động khách hàng — lịch sử tương tác/công việc/kinh doanh/chăm sóc theo dòng thời gian."""

    class ActivityType(models.TextChoices):
        # Tương tác
        CALL = "call", "Cuộc gọi"
        EMAIL = "email", "Email"
        MESSAGE = "message", "Tin nhắn"
        MEETING = "meeting", "Gặp mặt"
        NOTE = "note", "Ghi chú"
        # Công việc
        TASK = "task", "Công việc cần làm"
        FOLLOW_UP = "follow_up", "Follow-up"
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

    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField("Loại hoạt động", max_length=20, choices=ActivityType.choices)
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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_PROCESSED)
    follow_up_date = models.DateField("Ngày cần follow-up", null=True, blank=True)
    # Tuỳ chọn — vd khách hẹn "15h gọi lại" thì ghi rõ giờ, còn hẹn kiểu "thứ 4 tuần sau" thì để trống.
    follow_up_time = models.TimeField("Giờ hẹn nhắc", null=True, blank=True)
    # Tách riêng khỏi `status` — trạng thái hoạt động gốc (vd cuộc gọi đã "Hoàn thành") không
    # đồng nghĩa với việc đã nhắc/xử lý xong follow-up gắn với nó.
    follow_up_done = models.BooleanField("Đã nhắc follow-up", default=False)
    note = models.TextField("Ghi chú", blank=True)
    attachment = models.FileField("File đính kèm", upload_to="activities/%Y/%m/", null=True, blank=True)
    related_order = models.ForeignKey(
        Order, verbose_name="Đơn hàng liên quan", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    related_reference = models.CharField(
        "Tham chiếu khác (báo giá/hợp đồng/cơ hội/phiếu hỗ trợ...)", max_length=255, blank=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-activity_at"]

    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.title}"


class PriceInquiry(models.Model):
    """Hỏi giá — Kinh doanh mô tả lô hàng, Cung ứng trao đổi rồi chốt giá theo form riêng."""

    class Status(models.TextChoices):
        OPEN = "open", "Đang hỏi giá"
        QUOTED = "quoted", "Đã chốt giá"
        CANCELLED = "cancelled", "Huỷ"

    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="price_inquiries")
    description = models.TextField("Mô tả", blank=True)
    image = models.FileField("Hình ảnh", upload_to="price_inquiries/%Y/%m/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    cost_price = models.DecimalField("Giá vốn", max_digits=14, decimal_places=2, null=True, blank=True)
    floor_price = models.DecimalField("Giá sàn", max_digits=14, decimal_places=2, null=True, blank=True)
    ceiling_price = models.DecimalField("Giá trần", max_digits=14, decimal_places=2, null=True, blank=True)
    # Tỷ lệ sàn/trần tổng hợp của cả báo giá — theo quy định: khi gộp nhiều dịch vụ, tỷ lệ chung là
    # tỷ lệ sàn CAO NHẤT / tỷ lệ trần THẤP NHẤT trong các dịch vụ thành phần (không cộng dồn từng dòng).
    floor_pct = models.DecimalField("Tỷ lệ giá sàn (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    ceiling_pct = models.DecimalField("Tỷ lệ giá trần (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    quoted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Người chốt giá", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+"
    )
    quoted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Price inquiries"

    def __str__(self):
        return f"Hỏi giá #{self.pk} — {self.customer}"


class PriceInquiryMessage(models.Model):
    """Trao đổi qua lại giữa Kinh doanh và Cung ứng trong một yêu cầu hỏi giá."""

    inquiry = models.ForeignKey(PriceInquiry, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    content = models.TextField()
    # Đánh dấu tin nhắn hệ thống tự sinh khi chốt giá, để hiển thị khác trong luồng trao đổi.
    is_quote = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} — {self.content[:40]}"


class PriceListItem(models.Model):
    """Bảng giá dịch vụ chuẩn — Cung ứng chọn từ đây khi lên chi tiết báo giá cho một Hỏi giá."""

    class Category(models.TextChoices):
        I = "I", "Loại I"
        II = "II", "Loại II"
        III = "III", "Loại III"

    category = models.CharField("Phân loại", max_length=5, choices=Category.choices)
    group_name = models.CharField("Nhóm dịch vụ", max_length=255)
    group_code = models.CharField("Mã nhóm", max_length=10)
    item_code = models.CharField("Mã dịch vụ", max_length=20, unique=True)
    name = models.CharField("Tên dịch vụ", max_length=255)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    floor_pct = models.DecimalField("Giá sàn (%)", max_digits=6, decimal_places=2, default=0)
    ceiling_pct = models.DecimalField("Giá trần (%)", max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group_code", "item_code"]

    def __str__(self):
        return f"{self.item_code} — {self.name}"


class PriceInquiryQuoteLine(models.Model):
    """Một dòng mặt hàng/dịch vụ trong báo giá chi tiết của một Hỏi giá — Cung ứng nhập sau khi trao đổi xong."""

    inquiry = models.ForeignKey(PriceInquiry, on_delete=models.CASCADE, related_name="quote_lines")
    item = models.ForeignKey(PriceListItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # Snapshot lại tại thời điểm thêm dòng — bảng giá gốc có đổi sau này cũng không ảnh hưởng báo giá đã lập.
    item_name = models.CharField("Tên dịch vụ", max_length=255)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    floor_pct = models.DecimalField("Giá sàn (%)", max_digits=6, decimal_places=2, default=0)
    ceiling_pct = models.DecimalField("Giá trần (%)", max_digits=6, decimal_places=2, default=0)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, default=1)
    unit_cost = models.DecimalField("Đơn giá vốn", max_digits=14, decimal_places=2, default=0)
    note = models.TextField("Mô tả", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

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


class Quotation(models.Model):
    """Báo giá chính thức gửi khách hàng — tạo từ 1 Hỏi giá đã chốt giá nội bộ, copy lại dữ liệu
    đã có (mô tả + các dòng dịch vụ) và cho chỉnh sửa tiếp trước khi gửi khách, độc lập với Hỏi giá gốc."""

    # 1 Hỏi giá có thể có nhiều báo giá đã lưu song song (vd nhiều phương án giá gửi khách) — mỗi cái
    # độc lập, Xuất PDF/Tạo đơn/Xoá riêng từng cái.
    inquiry = models.ForeignKey(PriceInquiry, on_delete=models.CASCADE, related_name="quotations")
    note = models.TextField("Mô tả", blank=True)
    # Giá tổng báo giá phải nằm trong [giá sàn, giá trần] của Hỏi giá gốc mới lưu được trực tiếp —
    # nếu không, phải gửi đề xuất qua đây cho Cung ứng duyệt trước, duyệt xong mới lưu tiếp được.
    pending_approval = models.ForeignKey(
        "approvals.ApprovalRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Snapshot nội dung (note + lines) đã gửi kèm đề xuất — không có chỗ nào khác lưu lại nội dung
    # đang chờ duyệt, nên trước đây sau khi gửi đề xuất rồi tải lại trang thì y như mất hết, chỉ còn
    # thấy bản đã lưu lần gần nhất. Giữ snapshot này để mở lại đúng nội dung đang chờ/đã duyệt.
    pending_snapshot = models.JSONField(null=True, blank=True)
    # Thời điểm bấm "Lưu báo giá" gần nhất — None nghĩa là báo giá vừa tạo, chưa từng lưu lần nào.
    # Không dùng updated_at != created_at để suy ra việc này được, vì auto_now/auto_now_add gọi
    # timezone.now() 2 lần riêng biệt ngay lúc tạo, nên gần như luôn khác nhau dù chưa ai bấm Lưu.
    saved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Báo giá #{self.pk} — {self.inquiry.customer}"


class QuotationLine(models.Model):
    """Một dòng trong báo giá gửi khách — chỉ giữ những gì khách cần thấy (mô tả/ĐVT/SL/giá),
    bỏ hết chi tiết giá vốn/% nội bộ vì về sau chỉ cần quan tâm giá tổng của báo giá.
    `price` mặc định lấy từ giá sàn của dòng Hỏi giá gốc lúc tạo, sau đó chỉnh sửa độc lập."""

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="lines")
    item_name = models.CharField("Mô tả", max_length=255, blank=True)
    unit = models.CharField("ĐVT", max_length=50, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, default=1)
    price = models.DecimalField("Giá", max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.price


class Task(models.Model):
    """Công việc — có thể tạo độc lập, từ một Hoạt động khách hàng, hoặc từ Chat."""

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
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    attachment = models.FileField("File liên quan", upload_to="tasks/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "-created_at"]

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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kpi_targets")
    year = models.IntegerField()
    month = models.IntegerField()
    revenue_target = models.DecimalField("Chỉ tiêu doanh thu", max_digits=16, decimal_places=2, default=0)
    new_customer_target = models.IntegerField("Chỉ tiêu khách hàng mới", default=0)
    quote_target = models.IntegerField("Chỉ tiêu báo giá", default=0)
    order_target = models.IntegerField("Chỉ tiêu đơn hàng", default=0)
    task_target = models.IntegerField("Chỉ tiêu công việc hoàn thành", default=0)

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ["user", "year", "month"]

    def __str__(self):
        return f"KPI {self.user} — {self.month:02d}/{self.year}"


class Notice(models.Model):
    code = models.CharField("Số hiệu", max_length=50, blank=True)
    title = models.CharField("Tiêu đề", max_length=255)
    body = models.TextField("Nội dung", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
