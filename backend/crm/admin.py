from django.contrib import admin
from import_export.admin import ImportExportMixin, ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource
from config.admin_utils import linked_fk
from ops.models import Shipment as OpsShipment

from .models import (
    Activity,
    KPITarget,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceRequest,
    PriceRequestItem,
    PriceCalculation,
    PriceCalculationItem,
    PriceInquiryMessage,
    PriceInquiryQuoteLine,
    PriceInquiryQuoteLineBid,
    PriceListItem,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseRequestAllocation,
    Quotation,
    QuotationLine,
    SupplierQuote,
    Task,
)


class PartnerResource(ExcelModelResource):
    class Meta:
        model = Partner


class OrderResource(ExcelModelResource):
    class Meta:
        model = Order
        exclude = ("image",)  # FileField — không xuất/nhập file qua Excel


class NoticeResource(ExcelModelResource):
    class Meta:
        model = Notice


class ActivityResource(ExcelModelResource):
    class Meta:
        model = Activity
        # File Excel "Hoạt động đối tác" khớp đúng cột + thứ tự mẫu anh gửi, cộng thêm "Đối tác" ở
        # đầu — thiếu cột này thì không biết dòng nào của đối tác nào (mỗi dòng chỉ có ID số, không
        # tra ngược lại được). Không lặp lại Công ty (Đối tác đã đủ để tra cứu) hay các cột trách
        # nhiệm/nhật ký hệ thống (Người thực hiện/phụ trách/tạo, Ngày cập nhật) — các field bị bỏ
        # KHÔNG bị xoá khỏi model, chỉ ẩn khỏi riêng file Excel này. Dùng "fields" (danh sách + thứ
        # tự tường minh) thay vì "exclude" vì thứ tự mẫu không trùng thứ tự khai báo field trên model
        # (vd Trạng thái nằm sau Kết quả, không phải đầu).
        fields = (
            "id", "customer", "activity_type", "title", "activity_at", "contact_person", "content",
            "result", "status", "follow_up_date", "note", "attachment", "related_reference",
            "created_at", "related_order", "follow_up_done", "follow_up_time",
        )


class TaskResource(ExcelModelResource):
    class Meta:
        model = Task
        exclude = ("attachment",)  # FileField — không xuất/nhập file qua Excel


class KPITargetResource(ExcelModelResource):
    class Meta:
        model = KPITarget


class PriceRequestResource(ExcelModelResource):
    class Meta:
        model = PriceRequest
        # Bỏ "Công ty" khỏi sheet — chỉ còn đúng 1 công ty (LIVI), không còn tác dụng lọc/phân biệt.
        exclude = ("company",)


class PriceRequestItemResource(ExcelModelResource):
    class Meta:
        model = PriceRequestItem
        exclude = ("image",)  # FileField — không xuất/nhập file qua Excel


class PriceInquiryQuoteLineResource(ExcelModelResource):
    class Meta:
        model = PriceInquiryQuoteLine


class PriceInquiryQuoteLineBidResource(ExcelModelResource):
    class Meta:
        model = PriceInquiryQuoteLineBid


class QuotationResource(ExcelModelResource):
    class Meta:
        model = Quotation


class PriceListItemResource(ExcelModelResource):
    class Meta:
        model = PriceListItem


class CustomerFieldMixin:
    """Field "customer" (Khách hàng) trên Order/PriceRequest chỉ nên cho chọn Đối tác có
    is_customer=True — không thì 1 Đối tác chỉ đăng ký "Nhà cung cấp" (vd Chị Lụa) vẫn hiện ra khi
    tạo Đơn hàng/Hỏi giá mới, dù field này ghi rõ là "Khách hàng". KHÔNG áp dụng cho Activity (xem
    ActivityAdmin) — Hoạt động đối tác ghi nhận tương tác với cả khách hàng lẫn nhà cung cấp."""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            kwargs["queryset"] = Partner.objects.filter(is_customer=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fk_name = "customer"
    fields = ("activity_type", "title", "status", "activity_at", "performed_by")
    readonly_fields = ("created_by", "created_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


# 3 inline dưới đây CHỈ ĐỌC (không cho thêm/sửa trực tiếp tại đây) — mục đích là để mở 1 Đối tác ra
# là THẤY NGAY toàn bộ Hỏi giá/Đơn hàng/Yêu cầu nâng hạng đã gắn với đối tác đó (trước đây các bảng
# này hoàn toàn tách rời, chỉ nối ngầm qua field "Khách hàng"/"Đối tác" nên không nhìn thấy được
# mối liên kết nếu không biết trước). "show_change_link" cho bấm thẳng vào 1 dòng để mở trang đầy
# đủ của Hỏi giá/Đơn hàng đó (sửa chi tiết, xem tin nhắn trao đổi... vẫn làm ở trang riêng, đủ chỗ
# hơn — trang Đối tác chỉ để xem tổng quan).
class PriceRequestInline(admin.TabularInline):
    model = PriceRequest
    fk_name = "customer"
    extra = 0
    fields = ("id", "status", "assigned_to", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderInline(admin.TabularInline):
    model = Order
    fk_name = "customer"
    extra = 0
    fields = ("id", "status", "paid", "total", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ShipmentInline(admin.TabularInline):
    model = OpsShipment
    fk_name = "partner"
    extra = 0
    fields = ("id", "description", "tracking_code", "vh_status", "kt_status", "created_at")
    readonly_fields = fields
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Partner)
class PartnerAdmin(ImportExportModelAdmin):
    resource_classes = [PartnerResource]
    # Mỗi Đối tác chỉ có 1 dòng — hiện hết field trên bảng danh sách (kéo ngang xem), chỉ Hoạt động/
    # Đơn hàng/Hỏi giá (1 đối tác có NHIỀU dòng) mới tách bảng riêng theo mã đối tác.
    # Thứ tự cột khớp đúng file Excel mẫu anh gửi (Id đối tác, Là khách hàng, Là nhà cung cấp, Tên
    # đối tác, Người liên hệ, Số điện thoại, Id nhân sự phụ trách, Mô tả thêm, Xếp hạng, Địa chỉ,
    # Trạng thái, Người tạo, Ngày tạo, Ngày cập nhật).
    list_display = (
        "code", "is_customer", "is_supplier", "name", "contact_person", "phone", "assigned_to",
        "note", "tier_override", "address", "status", "created_by", "created_at", "updated_at",
    )
    # Bỏ "companies" khỏi bộ lọc — chỉ còn đúng 1 công ty (LIVI) nên không còn tác dụng lọc/phân biệt
    # gì nữa (xem companies/admin.py). Field companies vẫn giữ trong form thêm/sửa (filter_horizontal)
    # vì logic phân quyền theo công ty trong code vẫn dựa vào đó.
    list_filter = ("is_customer", "is_supplier", "status", "assigned_to")
    search_fields = ("code", "name", "contact_person", "phone")
    readonly_fields = ("code", "created_by", "created_at", "updated_at")
    filter_horizontal = ("companies",)
    # Hồ sơ nhân sự có thể ngày càng nhiều — dùng ô tìm kiếm (autocomplete) thay vì dropdown liệt kê hết.
    autocomplete_fields = ["assigned_to"]
    inlines = [PriceRequestInline, OrderInline, ShipmentInline, ActivityInline]


@admin.register(Order)
class OrderAdmin(ImportExportMixin, CustomerFieldMixin, admin.ModelAdmin):
    resource_classes = [OrderResource]
    list_display = (
        "id", "customer_link", "status", "created_by", "source_quotation_link", "received_by", "received_at",
        "confirmed_by", "confirmed_at", "description", "note", "paid", "on_platform",
        "pickup_point", "pickup_ward", "delivery_point", "delivery_ward", "weight_kg", "cod_amount",
        "floor_pct", "ceiling_pct", "floor_price", "ceiling_price", "total", "gross_profit",
        "created_at", "updated_at",
    )
    list_filter = ("status", "paid", "on_platform")
    inlines = [OrderItemInline]
    autocomplete_fields = ["pickup_ward", "delivery_ward"]
    # Chỉ còn đúng 1 công ty (LIVI) đang hoạt động — field tự điền qua default=get_default_company_id
    # (xem crm/models.py), ẩn hẳn khỏi form thêm/sửa cho gọn, không bắt chọn tay 1 lựa chọn duy nhất.
    exclude = ("company",)

    @admin.display(description="Khách hàng")
    def customer_link(self, obj):
        return linked_fk(obj.customer)

    @admin.display(description="Báo giá gốc")
    def source_quotation_link(self, obj):
        return linked_fk(obj.source_quotation)


@admin.register(Notice)
class NoticeAdmin(ImportExportModelAdmin):
    resource_classes = [NoticeResource]
    list_display = ("code", "title", "body", "created_by", "created_at")
    # Field tự điền qua default=get_default_company_id (xem crm/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)


@admin.register(Activity)
class ActivityAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_classes = [ActivityResource]
    # KHÔNG dùng CustomerFieldMixin (khác Order/PriceRequest — 2 cái đó chỉ áp dụng cho khách hàng
    # thật sự) — Hoạt động đối tác ghi nhận tương tác với CẢ khách hàng lẫn nhà cung cấp (vd gọi điện
    # thương lượng với nhà cung cấp), nên dropdown "Đối tác" phải cho chọn mọi Đối tác, không chỉ
    # is_customer=True.
    # Bảng hiện trên trang Admin khớp đúng cột + thứ tự với file Excel (ActivityResource) — trang này
    # đóng vai trò như 1 "sheet" sống, phải nhất quán với file xuất ra, không lệch nhau. "Đối tác" ở
    # đầu bảng — thiếu cột này thì không biết dòng nào của đối tác nào.
    list_display = (
        "customer_link", "activity_type", "title", "activity_at", "contact_person", "content",
        "result", "status", "follow_up_date", "note", "attachment", "related_reference",
        "created_at", "related_order", "follow_up_done", "follow_up_time",
    )
    list_filter = ("activity_type", "status")
    search_fields = ("title", "content")
    # Field tự điền qua default=get_default_company_id (xem crm/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)

    @admin.display(description="Đối tác")
    def customer_link(self, obj):
        return linked_fk(obj.customer)


@admin.register(Task)
class TaskAdmin(ImportExportModelAdmin):
    resource_classes = [TaskResource]
    list_display = (
        "title", "content", "assigned_to", "created_by", "partner_link", "related_activity",
        "priority", "status", "due_at", "created_at", "updated_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "content")
    # Field tự điền qua default=get_default_company_id (xem crm/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)

    @admin.display(description="Khách hàng/đối tác liên quan")
    def partner_link(self, obj):
        return linked_fk(obj.partner)


@admin.register(KPITarget)
class KPITargetAdmin(ImportExportModelAdmin):
    resource_classes = [KPITargetResource]
    exclude = ("company",)
    list_display = ("user", "year", "month", "revenue_target", "new_customer_target", "quote_target", "order_target", "task_target")
    list_filter = ("year", "month")


class PriceInquiryMessageInline(admin.TabularInline):
    model = PriceInquiryMessage
    extra = 0
    readonly_fields = ("author", "created_at")


class PriceInquiryQuoteLineInline(admin.TabularInline):
    model = PriceInquiryQuoteLine
    extra = 0
    readonly_fields = ("created_by", "created_at")


class PriceRequestItemInline(admin.TabularInline):
    model = PriceRequestItem
    extra = 1
    fields = ("product", "item_name", "image", "quantity", "unit", "source_status", "estimated_cost_price")
    readonly_fields = ("source_status",)


@admin.register(PriceRequest)
class PriceRequestAdmin(ImportExportMixin, CustomerFieldMixin, admin.ModelAdmin):
    resource_classes = [PriceRequestResource]
    # Khớp đúng cột + thứ tự với PriceRequestResource (xem quy tắc: trang Admin luôn là bản xem trực
    # tiếp của cùng dữ liệu xuất ra Excel, không lệch nhau). Sản phẩm/số lượng giờ nằm ở inline
    # PriceRequestItem (1 Yêu cầu giá có nhiều sản phẩm), không còn là cột trực tiếp ở đây.
    list_display = (
        "code", "customer_link", "assigned_to", "country", "province",
        "district", "ward", "street_address", "description", "status", "created_by",
        "created_at", "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("code", "customer__name")
    readonly_fields = ("code",)
    autocomplete_fields = ["country", "province", "district", "ward", "assigned_to"]
    inlines = [PriceRequestItemInline, PriceInquiryQuoteLineInline, PriceInquiryMessageInline]
    # Field tự điền qua default=get_default_company_id (xem crm/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)

    @admin.display(description="Khách hàng")
    def customer_link(self, obj):
        return linked_fk(obj.customer)


# Đăng ký riêng (không chỉ để inline trong Yêu cầu giá) để PurchaseRequestAllocation/
# InventoryReservation bên dưới (kể cả ở app inventory) autocomplete được tới đúng dòng.
@admin.register(PriceRequestItem)
class PriceRequestItemAdmin(ImportExportModelAdmin):
    resource_classes = [PriceRequestItemResource]
    list_display = (
        "price_request", "product", "item_name", "quantity", "unit", "source_status", "estimated_cost_price",
    )
    list_filter = ("source_status",)
    search_fields = ("item_name", "price_request__code")
    readonly_fields = ("source_status",)
    autocomplete_fields = ["price_request", "product"]


class PurchaseRequestResource(ExcelModelResource):
    class Meta:
        model = PurchaseRequest


class PurchaseRequestItemResource(ExcelModelResource):
    class Meta:
        model = PurchaseRequestItem


class PurchaseRequestAllocationResource(ExcelModelResource):
    class Meta:
        model = PurchaseRequestAllocation


class SupplierQuoteResource(ExcelModelResource):
    class Meta:
        model = SupplierQuote


class SupplierFieldMixin:
    """Field "supplier" trên SupplierQuote/StockMovement... chỉ nên cho chọn Đối tác có
    is_supplier=True — đối xứng với CustomerFieldMixin ở trên (áp dụng ngược lại)."""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "supplier":
            kwargs["queryset"] = Partner.objects.filter(is_supplier=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PurchaseRequestAllocationInline(admin.TabularInline):
    model = PurchaseRequestAllocation
    extra = 1
    autocomplete_fields = ["price_request_item"]


class SupplierQuoteInline(SupplierFieldMixin, admin.TabularInline):
    model = SupplierQuote
    extra = 0
    readonly_fields = ("created_by", "created_at")
    autocomplete_fields = ["supplier"]


class PurchaseRequestItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(ImportExportModelAdmin):
    resource_classes = [PurchaseRequestResource]
    list_display = ("code", "purchase_type", "warehouse", "note", "created_by", "created_at", "updated_at")
    list_filter = ("purchase_type", "warehouse")
    search_fields = ("code",)
    readonly_fields = ("code",)
    autocomplete_fields = ["warehouse"]
    inlines = [PurchaseRequestItemInline]


# Đăng ký riêng để SupplierQuote/PurchaseRequestAllocation/Lot (kể cả ở app inventory) autocomplete
# được tới đúng dòng đề nghị mua.
@admin.register(PurchaseRequestItem)
class PurchaseRequestItemAdmin(ImportExportModelAdmin):
    resource_classes = [PurchaseRequestItemResource]
    list_display = ("purchase_request", "product", "item_name", "quantity", "unit")
    search_fields = ("item_name", "purchase_request__code")
    autocomplete_fields = ["purchase_request", "product"]
    inlines = [SupplierQuoteInline, PurchaseRequestAllocationInline]


@admin.register(SupplierQuote)
class SupplierQuoteAdmin(SupplierFieldMixin, ImportExportModelAdmin):
    resource_classes = [SupplierQuoteResource]
    list_display = (
        "purchase_request_item", "supplier", "unit_price", "quantity", "unit", "pickup_point",
        "total_packages", "package_dimensions", "total_cbm", "total_weight_kg", "available_at",
        "payment_terms", "delivery_terms", "shipping_cost", "note", "is_selected", "selection_note",
        "created_by", "created_at",
    )
    list_filter = ("is_selected",)
    search_fields = ("supplier__name", "purchase_request_item__item_name")
    autocomplete_fields = ["purchase_request_item", "supplier"]


class PriceCalculationResource(ExcelModelResource):
    class Meta:
        model = PriceCalculation


class PriceCalculationItemResource(ExcelModelResource):
    class Meta:
        model = PriceCalculationItem


class PriceCalculationItemInline(admin.TabularInline):
    model = PriceCalculationItem
    extra = 1
    autocomplete_fields = ["price_request_item"]


@admin.register(PriceCalculation)
class PriceCalculationAdmin(ImportExportModelAdmin):
    resource_classes = [PriceCalculationResource]
    list_display = (
        "price_request", "version", "profit_pct", "approval_status", "approved_by", "approved_at",
        "created_by", "created_at",
    )
    list_filter = ("approval_status",)
    search_fields = ("price_request__code",)
    readonly_fields = ("version",)
    autocomplete_fields = ["price_request"]
    inlines = [PriceCalculationItemInline]


# Đăng ký riêng (không chỉ để inline trong Hỏi giá) để Báo giá cạnh tranh bên dưới autocomplete được
# tới đúng dòng, và để bấm xem "Báo giá thắng" (winning_bid) round-trip qua lại được.
@admin.register(PriceInquiryQuoteLine)
class PriceInquiryQuoteLineAdmin(ImportExportModelAdmin):
    resource_classes = [PriceInquiryQuoteLineResource]
    list_display = (
        "id", "inquiry_link", "item_name", "quantity", "unit", "unit_cost", "winning_bid",
        "note", "created_by", "created_at",
    )
    search_fields = ("item_name",)
    autocomplete_fields = ["inquiry", "item"]

    @admin.display(description="Hỏi giá")
    def inquiry_link(self, obj):
        return linked_fk(obj.inquiry)


@admin.register(PriceInquiryQuoteLineBid)
class PriceInquiryQuoteLineBidAdmin(ImportExportModelAdmin):
    resource_classes = [PriceInquiryQuoteLineBidResource]
    list_display = ("id", "quote_line_link", "bidder", "unit_cost", "note", "created_at")
    search_fields = ("quote_line__item_name",)
    autocomplete_fields = ["quote_line"]

    @admin.display(description="Dòng dịch vụ cấu thành")
    def quote_line_link(self, obj):
        return linked_fk(obj.quote_line)


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(ImportExportModelAdmin):
    resource_classes = [QuotationResource]
    list_display = (
        "id", "inquiry_link", "note", "pending_approval", "saved_at", "created_by",
        "created_at", "updated_at",
    )
    inlines = [QuotationLineInline]

    @admin.display(description="Hỏi giá")
    def inquiry_link(self, obj):
        return linked_fk(obj.inquiry)


@admin.register(PriceListItem)
class PriceListItemAdmin(ImportExportModelAdmin):
    resource_classes = [PriceListItemResource]
    list_display = ("item_code", "category", "group_code", "group_name", "name", "unit", "floor_pct", "ceiling_pct", "is_active")
    list_filter = ("category", "group_code", "is_active")
    search_fields = ("item_code", "name", "group_name")
    list_editable = ("floor_pct", "ceiling_pct", "is_active")
    # Field tự điền qua default=get_default_company_id (xem crm/models.py), ẩn khỏi form cho gọn.
    exclude = ("company",)
