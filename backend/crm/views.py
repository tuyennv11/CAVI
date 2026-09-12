import base64
import io
import mimetypes
from datetime import timedelta
from decimal import Decimal

import qrcode
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_manager, is_supply
from approvals.models import ApprovalRequest
from companies.mixins import CompanyScopedMixin
from inventory.models import StockMovement, Warehouse

from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    Activity,
    Notice,
    Order,
    OrderItem,
    Partner,
    PriceInquiry,
    PriceInquiryQuoteLine,
    PriceInquiryQuoteLineBid,
    PriceListItem,
    Quotation,
    QuotationLine,
    Task,
    TierUpgradeRequest,
)
from .permissions import IsAssignedOrCreatorOrManager, IsManagerOrAssignedSales, IsManagerOrSupply
from .serializers import (
    ActivitySerializer,
    NoticeSerializer,
    OrderSerializer,
    PartnerSerializer,
    PriceInquiryMessageSerializer,
    PriceInquiryQuoteLineBidSerializer,
    PriceInquiryQuoteLineSerializer,
    PriceInquirySerializer,
    PriceListItemSerializer,
    QuotationSerializer,
    TaskSerializer,
    TierUpgradeRequestSerializer,
)

MONEY_FIELD = DecimalField(max_digits=16, decimal_places=2)


def _format_money_vn(value):
    return f"{Decimal(value):,.0f}".replace(",", ".") + " đ"


def _format_qty_vn(value):
    return f"{Decimal(value):.2f}".rstrip("0").rstrip(".") or "0"


def _sum_revenue(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(F("items__quantity") * F("items__unit_price"), output_field=MONEY_FIELD), 0, output_field=MONEY_FIELD
        )
    )["total"]


def _company_logo_data_uri(company):
    # Logo riêng từng công ty (upload qua admin) — nếu công ty mới chưa kịp có logo, dùng tạm logo
    # tĩnh mặc định để PDF không bị vỡ layout (thiếu ảnh) trong lúc chờ.
    if company is not None and company.logo:
        mime = mimetypes.guess_type(company.logo.name)[0] or "image/png"
        with company.logo.open("rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    logo_path = finders.find("crm/logo.jpg")
    if logo_path:
        with open(logo_path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    return ""


def _sum_gross_profit(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum(
                F("items__quantity") * (F("items__unit_price") - F("items__unit_cost")),
                output_field=MONEY_FIELD,
            ),
            0,
            output_field=MONEY_FIELD,
        )
    )["total"]


class PartnerViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    """Đối tác dùng CHUNG cho mọi công ty — KHÔNG lọc queryset theo công ty (khác mọi ViewSet khác
    trong file này). `CompanyScopedMixin` chỉ dùng để lấy `get_active_company()` cho context của
    serializer (tính hạng/công nợ đúng theo công ty đang xem, xem PartnerSerializer)."""

    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    search_fields = ["name", "contact_person", "phone"]
    filterset_fields = ["assigned_to", "is_customer", "is_supplier"]

    def get_queryset(self):
        qs = Partner.objects.select_related("assigned_to").all()
        if is_manager(self.request.user):
            return qs
        return qs.filter(assigned_to=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self.get_active_company()
        return context

    def perform_create(self, serializer):
        # Nhân viên kinh doanh tạo đối tác mới thì mặc định tự phụ trách đối tác đó.
        if is_manager(self.request.user) and serializer.validated_data.get("assigned_to"):
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)

    def _get_partner(self, request, pk):
        # Không dùng self.get_object() ở đây — nó áp cả filter_backends (vd search_fields của
        # Partner) lên chính request này, và các action con bên dưới cũng dùng query param
        # "search"/"assigned_to" riêng cho Activity nên bị đụng nhau, gây 404 sai.
        partner = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, partner)
        return partner

    @action(detail=True, methods=["get", "post"], url_path="activities")
    def activities(self, request, pk=None):
        partner = self._get_partner(request, pk)
        if request.method == "GET":
            qs = partner.activities.select_related(
                "performed_by", "assigned_to", "created_by", "related_order"
            ).filter(company=self.get_active_company())
            p = request.query_params
            if p.get("activity_type"):
                qs = qs.filter(activity_type=p["activity_type"])
            if p.get("assigned_to"):
                qs = qs.filter(assigned_to_id=p["assigned_to"])
            if p.get("performed_by"):
                qs = qs.filter(performed_by_id=p["performed_by"])
            if p.get("status"):
                qs = qs.filter(status=p["status"])
            if p.get("has_follow_up") == "true":
                qs = qs.filter(follow_up_date__isnull=False)
            elif p.get("has_follow_up") == "false":
                qs = qs.filter(follow_up_date__isnull=True)
            if p.get("date_from"):
                qs = qs.filter(activity_at__date__gte=p["date_from"])
            if p.get("date_to"):
                qs = qs.filter(activity_at__date__lte=p["date_to"])
            if p.get("search"):
                term = p["search"]
                qs = qs.filter(Q(title__icontains=term) | Q(content__icontains=term))
            return Response(ActivitySerializer(qs, many=True).data)

        data = request.data.copy()
        data["customer"] = partner.id
        serializer = ActivitySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            customer=partner,
            company=self.get_active_company(),
            created_by=request.user,
            performed_by=serializer.validated_data.get("performed_by") or request.user,
        )
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"], url_path="activities/summary")
    def activities_summary(self, request, pk=None):
        partner = self._get_partner(request, pk)
        acts = partner.activities.filter(company=self.get_active_company())
        today = timezone.localdate()
        last = acts.order_by("-activity_at").first()
        return Response(
            {
                "total_activities": acts.count(),
                "last_activity_at": last.activity_at if last else None,
                "upcoming_follow_ups": acts.filter(
                    follow_up_date__isnull=False, follow_up_date__gte=today, follow_up_done=False
                ).count(),
            }
        )


class ActivityViewSet(CompanyScopedMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Chỉ hỗ trợ cập nhật (vd đánh dấu đã nhắc follow-up) — tạo/xem hoạt động đi qua PartnerViewSet.activities."""

    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.scope_by_company(
            Activity.objects.select_related("customer", "performed_by", "assigned_to").all()
        )
        if is_manager(self.request.user):
            return qs
        return qs.filter(Q(assigned_to=self.request.user) | Q(customer__assigned_to=self.request.user)).distinct()


class TaskViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsAssignedOrCreatorOrManager]
    filterset_fields = ["status", "priority", "assigned_to", "partner"]

    def get_queryset(self):
        company = self.get_active_company()
        qs = Task.objects.select_related("assigned_to", "created_by", "partner").filter(
            Q(company__isnull=True) | Q(company=company)
        )
        if not is_manager(self.request.user):
            qs = qs.filter(Q(assigned_to=self.request.user) | Q(created_by=self.request.user))

        p = self.request.query_params
        today = timezone.localdate()
        open_statuses = [Task.Status.TODO, Task.Status.IN_PROGRESS]
        if p.get("due") == "today":
            qs = qs.filter(due_at__date=today, status__in=open_statuses)
        elif p.get("due") == "overdue":
            qs = qs.filter(due_at__date__lt=today, status__in=open_statuses)
        elif p.get("due") == "upcoming":
            qs = qs.filter(due_at__date__gt=today, status__in=open_statuses)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_active_company())


class PriceInquiryViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PriceInquirySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["customer", "status"]

    def get_queryset(self):
        qs = self.scope_by_company(
            PriceInquiry.objects.select_related("customer", "created_by", "quoted_by").prefetch_related(
                "messages__author"
            )
        )
        if is_manager(self.request.user):
            return qs
        return qs.filter(customer__assigned_to=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_active_company())

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        inquiry = self.get_object()
        if request.method == "GET":
            return Response(PriceInquiryMessageSerializer(inquiry.messages.all(), many=True).data)
        serializer = PriceInquiryMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(inquiry=inquiry, author=request.user)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get", "post"], url_path="lines")
    def lines(self, request, pk=None):
        inquiry = self.get_object()
        if request.method == "GET":
            return Response(PriceInquiryQuoteLineSerializer(inquiry.quote_lines.all(), many=True).data)
        serializer = PriceInquiryQuoteLineSerializer(data=request.data, context={"inquiry": inquiry})
        serializer.is_valid(raise_exception=True)
        serializer.save(inquiry=inquiry, created_by=request.user)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], url_path="confirm-quote")
    def confirm_quote(self, request, pk=None):
        inquiry = self.get_object()
        lines = list(inquiry.quote_lines.all())
        if not lines:
            raise ValidationError("Cần thêm ít nhất 1 dòng báo giá trước khi xác nhận.")
        cents = Decimal("0.01")
        total_cost = sum((line.line_cost for line in lines), Decimal("0")).quantize(cents)
        # Quy định: khi báo giá gộp nhiều dịch vụ, tỷ lệ sàn/trần CHUNG của cả báo giá là tỷ lệ sàn
        # CAO NHẤT / tỷ lệ trần THẤP NHẤT trong các dịch vụ thành phần — áp 1 lần lên tổng giá vốn,
        # không cộng dồn từng dòng riêng lẻ (line_floor/line_ceiling vẫn giữ để hiển thị theo dòng).
        combined_floor_pct = max(line.floor_pct for line in lines)
        combined_ceiling_pct = min(line.ceiling_pct for line in lines)
        total_floor = (total_cost * (1 + combined_floor_pct / 100)).quantize(cents)
        total_ceiling = (total_cost * (1 + combined_ceiling_pct / 100)).quantize(cents)
        inquiry.cost_price = total_cost
        inquiry.floor_price = total_floor
        inquiry.ceiling_price = total_ceiling
        inquiry.floor_pct = combined_floor_pct
        inquiry.ceiling_pct = combined_ceiling_pct
        inquiry.status = PriceInquiry.Status.QUOTED
        inquiry.quoted_by = request.user
        inquiry.quoted_at = timezone.now()
        inquiry.save()
        inquiry.messages.create(
            author=request.user,
            is_quote=True,
            content=(
                f"📌 Đã chốt giá — Giá vốn: {total_cost} · Giá sàn: {total_floor} ({combined_floor_pct}%) · "
                f"Giá trần: {total_ceiling} ({combined_ceiling_pct}%)"
            ),
        )
        return Response(PriceInquirySerializer(inquiry).data)

    @action(detail=True, methods=["post"], url_path="create-quotation")
    def create_quotation(self, request, pk=None):
        inquiry = self.get_object()
        if inquiry.status != PriceInquiry.Status.QUOTED:
            raise ValidationError("Chỉ có thể tạo báo giá sau khi đã chốt giá.")
        # 1 Hỏi giá cho phép nhiều báo giá đã lưu song song — nhưng chỉ 1 bản nháp (chưa lưu) tại 1
        # thời điểm, để tránh tích luỹ nháp bỏ dở không ai dọn. Đã có nháp thì trả lại đúng nháp đó.
        draft = inquiry.quotations.filter(saved_at__isnull=True).first()
        if draft is not None:
            return Response(QuotationSerializer(draft).data, status=200)
        quotation = Quotation.objects.create(inquiry=inquiry, note=inquiry.description, created_by=request.user)
        QuotationLine.objects.bulk_create(
            QuotationLine(
                quotation=quotation,
                product=line.product,
                # Đúng ô "Mô tả" (note) của dòng dịch vụ cấu thành, không lấy tên dịch vụ (item_name)
                # — 2 khái niệm khác nhau, không dùng cái này thay cho cái kia.
                item_name=line.note,
                unit=line.unit,
                quantity=line.quantity,
                # QuotationLine.price là đơn giá (line_total = quantity × price), còn line_floor là
                # TỔNG giá sàn của cả dòng (đã nhân số lượng) — phải chia lại cho số lượng mới ra đúng
                # đơn giá, nếu không tổng dòng báo giá sẽ bị nhân trùng số lượng 1 lần nữa. Kết quả cuối
                # (line_total) khớp đúng số đã hiển thị ở cột "Giá sàn" của bảng dịch vụ cấu thành ở trên.
                # Tổng các dòng có thể thấp hơn giá sàn CHUNG của cả Hỏi giá (tỷ lệ sàn cao nhất áp 1 lần
                # lên tổng) khi các dịch vụ có tỷ lệ sàn khác nhau — lúc đó phải Gửi đề xuất duyệt, đúng
                # theo quy định.
                price=line.line_floor / line.quantity,
            )
            for line in inquiry.quote_lines.all()
        )
        return Response(QuotationSerializer(quotation).data, status=201)


class QuotationViewSet(
    CompanyScopedMixin,
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated]
    company_field = "inquiry__company"

    def get_queryset(self):
        qs = self.scope_by_company(
            Quotation.objects.select_related("inquiry__customer").prefetch_related("lines")
        )
        if is_manager(self.request.user):
            return qs
        return qs.filter(inquiry__customer__assigned_to=self.request.user)

    def perform_update(self, serializer):
        # Đây là hành động "Lưu báo giá" thật sự (PATCH trực tiếp lên Quotation) — đánh dấu saved_at
        # để phân biệt với báo giá vừa tạo/đang chờ duyệt, chưa từng được lưu lần nào.
        serializer.save(saved_at=timezone.now())

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        quotation = self.get_object()
        lines_data = request.data.get("lines", [])
        note = request.data.get("note", quotation.note)
        total = sum(
            (Decimal(str(line.get("quantity", 1))) * Decimal(str(line.get("price", 0))) for line in lines_data),
            Decimal("0"),
        )
        inquiry = quotation.inquiry
        floor = inquiry.floor_price if inquiry.floor_price is not None else Decimal("0")
        ceiling = inquiry.ceiling_price
        if total >= floor and (ceiling is None or total <= ceiling):
            raise ValidationError("Giá tổng đã nằm trong khoảng giá sàn - giá trần, không cần gửi đề xuất.")
        approval = ApprovalRequest.objects.create(
            company=inquiry.company,
            request_type=ApprovalRequest.RequestType.PROPOSAL,
            category=f"Báo giá #{quotation.id}",
            title=f"Đề xuất báo giá ngoài khoảng giá sàn/trần — {inquiry.customer.name}",
            note=(
                f"Báo giá #{quotation.id} (Hỏi giá #{inquiry.id}) — Giá đề xuất: {total} "
                f"(giá sàn {floor}, giá trần {ceiling})."
            ),
            # Cho người duyệt bấm thẳng vào đây để xem lịch sử tương tác/báo giá trước khi quyết định,
            # thay vì chỉ thấy 1 dòng tóm tắt trên trang Ký duyệt.
            related_url=f"/partners/{inquiry.customer_id}?tab=inquiries&inquiry={inquiry.id}",
            amount=total,
            requested_by=request.user,
        )
        quotation.pending_approval = approval
        # Giữ lại đúng nội dung đã gửi kèm đề xuất — không có chỗ nào khác lưu nội dung đang chờ duyệt,
        # nên nếu chỉ dựa vào state phía trình duyệt thì tải lại trang là mất, nhìn như chưa lưu gì.
        quotation.pending_snapshot = {"note": note, "lines": lines_data}
        quotation.save()
        return Response(QuotationSerializer(quotation).data, status=201)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        # Import ở đây, không để trên đầu file — WeasyPrint cần thư viện hệ thống (pango/cairo/gdk-pixbuf)
        # chỉ có trên máy chủ Linux lúc deploy, import ở module-level sẽ làm cả app không chạy nổi trên
        # máy dev không có các thư viện đó.
        from weasyprint import HTML

        quotation = self.get_object()
        lines = quotation.lines.all()
        line_rows = [
            {
                "item_name": line.item_name,
                "unit": line.unit,
                "quantity_display": _format_qty_vn(line.quantity),
                "price_display": _format_money_vn(line.price),
                "total_display": _format_money_vn(line.line_total),
            }
            for line in lines
        ]
        total = sum((line.line_total for line in lines), Decimal("0"))
        company = quotation.inquiry.company

        html = render_to_string(
            "crm/quotation_pdf.html",
            {
                "quotation": quotation,
                "customer_name": quotation.inquiry.customer.name,
                "lines": line_rows,
                "total_display": _format_money_vn(total),
                "issue_date": quotation.updated_at.strftime("%d/%m/%Y"),
                "company_name": company.legal_name or company.name,
                "hotline": company.hotline or settings.COMPANY_HOTLINE,
                "logo_data_uri": _company_logo_data_uri(company),
            },
        )
        pdf_bytes = HTML(string=html).write_pdf()
        filename = slugify(f"bao-gia-{quotation.id}-{quotation.inquiry.customer.name}") + ".pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="create-order")
    def create_order(self, request, pk=None):
        quotation = self.get_object()
        inquiry = quotation.inquiry
        order = Order.objects.create(
            customer=inquiry.customer,
            company=inquiry.company,
            created_by=request.user,
            source_quotation=quotation,
            # Nội dung mô tả lô hàng cho Vận hành phải giống hệt Hỏi giá gốc — copy thẳng từ đó,
            # không tự nhập lại (Kinh doanh đã mô tả đầy đủ ngay từ lúc hỏi giá rồi).
            description=inquiry.description,
            image=inquiry.image if inquiry.image else None,
            # Xác định sẵn giá sàn/trần của đơn ngay lúc tạo, lấy từ Hỏi giá gốc — đã chốt theo đúng
            # quy tắc tỷ lệ sàn cao nhất/trần thấp nhất trong các dịch vụ thành phần.
            floor_pct=inquiry.floor_pct,
            ceiling_pct=inquiry.ceiling_pct,
            floor_price=inquiry.floor_price,
            ceiling_price=inquiry.ceiling_price,
        )
        OrderItem.objects.bulk_create(
            OrderItem(
                order=order,
                product=line.product,
                description=line.item_name,
                quantity=line.quantity,
                unit_price=line.price,
            )
            for line in quotation.lines.all()
        )
        return Response(OrderSerializer(order).data, status=201)


class PriceInquiryQuoteLineViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = PriceInquiryQuoteLineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["inquiry", "inquiry__status"]
    company_field = "inquiry__company"

    def get_queryset(self):
        qs = self.scope_by_company(
            PriceInquiryQuoteLine.objects.select_related("inquiry__customer").prefetch_related("bids__bidder")
        )
        if is_manager(self.request.user):
            return qs
        # Cung ứng thấy TOÀN BỘ dòng đang mở của cả công ty đang chọn (Sàn báo giá cạnh tranh) —
        # không giới hạn theo Hỏi giá mình phụ trách, khác hẳn Nhân viên kinh doanh chỉ thấy khách
        # của mình. Vẫn phải lọc theo công ty đang thao tác (scope_by_company ở trên) — nếu không,
        # Cung ứng của công ty này sẽ thấy luôn cả dữ liệu đấu giá của công ty khác.
        if is_supply(self.request.user):
            return qs.filter(inquiry__status=PriceInquiry.Status.OPEN)
        return qs.filter(inquiry__customer__assigned_to=self.request.user)

    @action(detail=True, methods=["post"])
    def award(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới chọn được giá thắng.")
        line = self.get_object()
        if line.inquiry.status != PriceInquiry.Status.OPEN:
            raise ValidationError("Hỏi giá này đã đóng, không thể đổi giá thắng nữa.")
        bid = get_object_or_404(PriceInquiryQuoteLineBid, pk=request.data.get("bid"), quote_line=line)
        line.winning_bid = bid
        line.unit_cost = bid.unit_cost
        line.save(update_fields=["winning_bid", "unit_cost"])
        return Response(PriceInquiryQuoteLineSerializer(line).data)


class PriceInquiryQuoteLineBidViewSet(
    CompanyScopedMixin,
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Chào giá trên Sàn báo giá cạnh tranh — không có Update (không cho sửa 1 giá đã chào, xem
    docstring PriceInquiryQuoteLineBid). Tạo/xoá qua đây; chọn giá thắng làm qua action "award" của
    PriceInquiryQuoteLineViewSet (không phải ở đây, vì đó là hành động trên Dòng, không phải trên
    bản thân Báo giá)."""

    serializer_class = PriceInquiryQuoteLineBidSerializer
    permission_classes = [IsAuthenticated, IsManagerOrSupply]
    filterset_fields = ["quote_line"]
    company_field = "quote_line__inquiry__company"

    def get_queryset(self):
        # Không lọc theo người dùng — Sàn chỉ có ý nghĩa nếu ai cũng thấy giá của nhau (đấu giá công
        # khai, không phải đấu thầu kín). IsManagerOrSupply đã chặn hẳn các vai trò khác ở has_permission.
        # Vẫn phải lọc theo công ty đang thao tác — nếu không, đây chính là nửa còn lại của rò rỉ dữ
        # liệu giữa các công ty trên Sàn báo giá cạnh tranh (xem PriceInquiryQuoteLineViewSet).
        return self.scope_by_company(
            PriceInquiryQuoteLineBid.objects.select_related("quote_line__inquiry", "bidder")
        )

    def perform_create(self, serializer):
        serializer.save(bidder=self.request.user)

    def perform_destroy(self, instance):
        # Xoá mất báo giá đang là "giá thắng" của 1 dòng thì mất luôn dấu vết ai đã thắng — chặn
        # hẳn, kể cả với Quản lý (không chỉ giới hạn quyền xoá theo has_object_permission).
        if PriceInquiryQuoteLine.objects.filter(winning_bid=instance).exists():
            raise ValidationError("Không thể xoá báo giá đã được chọn làm giá thắng — hãy chọn giá khác trước.")
        instance.delete()


class PriceListItemViewSet(CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PriceListItemSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "item_code", "group_name"]
    pagination_class = None

    def get_queryset(self):
        return self.scope_by_company(PriceListItem.objects.filter(is_active=True))


class TierUpgradeRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TierUpgradeRequestSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "partner"]

    def get_queryset(self):
        company = self.get_active_company()
        qs = TierUpgradeRequest.objects.select_related("partner", "requested_by", "reviewed_by").filter(
            Q(company__isnull=True) | Q(company=company)
        )
        if is_manager(self.request.user):
            return qs
        return qs.filter(partner__assigned_to=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user, company=self.get_active_company())

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới duyệt được yêu cầu nâng hạng.")
        tier_request = self.get_object()
        tier_request.status = TierUpgradeRequest.Status.APPROVED
        tier_request.reviewed_by = request.user
        tier_request.reviewed_at = timezone.now()
        tier_request.save()
        tier_request.partner.tier_override = tier_request.requested_tier
        tier_request.partner.save(update_fields=["tier_override"])
        return Response(TierUpgradeRequestSerializer(tier_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới từ chối được yêu cầu nâng hạng.")
        tier_request = self.get_object()
        tier_request.status = TierUpgradeRequest.Status.REJECTED
        tier_request.reviewed_by = request.user
        tier_request.reviewed_at = timezone.now()
        tier_request.save()
        return Response(TierUpgradeRequestSerializer(tier_request).data)


class OrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAssignedSales]
    filterset_fields = ["status", "customer", "paid", "on_platform"]

    def get_queryset(self):
        qs = self.scope_by_company(
            Order.objects.select_related("customer", "created_by").prefetch_related("items").all()
        )
        # Vận hành ghi nhận số liệu thực tế lúc nhận hàng không gắn với khách hàng cụ thể nào của
        # Kinh doanh nào — cần thấy được phiếu đang chờ nhận của TẤT CẢ khách CỦA CÔNG TY ĐANG CHỌN,
        # không chỉ khách mình phụ trách (lọc theo công ty ở scope_by_company trên vẫn áp dụng, chỉ
        # bỏ qua lọc theo người phụ trách). Xem thêm get_permissions bên dưới.
        if self.action in ("pending_receipt", "record_actual"):
            return qs
        if is_manager(self.request.user):
            return qs
        return qs.filter(customer__assigned_to=self.request.user)

    def get_permissions(self):
        if self.action in ("pending_receipt", "record_actual"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_active_company())

    @action(detail=False, methods=["get"], url_path="pending-receipt")
    def pending_receipt(self, request):
        qs = self.get_queryset().filter(
            status__in=[Order.Status.PENDING_RECEIPT, Order.Status.PENDING_CONFIRMATION]
        )
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="record-actual")
    def record_actual(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.Status.PENDING_RECEIPT, Order.Status.PENDING_CONFIRMATION):
            raise ValidationError("Chỉ ghi nhận số liệu thực tế khi phiếu đang chờ vận hành nhận hàng.")
        actual_by_id = {}
        for item_data in request.data.get("items", []):
            item_id = item_data.get("id")
            actual = item_data.get("actual_quantity")
            if item_id is not None and actual not in (None, ""):
                actual_by_id[item_id] = actual
        for item in order.items.all():
            if item.id in actual_by_id:
                item.actual_quantity = actual_by_id[item.id]
                item.save(update_fields=["actual_quantity"])
        order.status = Order.Status.PENDING_CONFIRMATION
        order.received_by = request.user
        order.received_at = timezone.now()
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="confirm-received")
    def confirm_received(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.Status.PENDING_CONFIRMATION:
            raise ValidationError("Chỉ xác nhận sau khi Vận hành đã ghi nhận số liệu thực tế nhận hàng.")
        for item in order.items.all():
            if item.actual_quantity is not None and item.actual_quantity != item.quantity:
                item.quantity = item.actual_quantity
                item.save(update_fields=["quantity"])
        order.status = Order.Status.NEW
        order.confirmed_by = request.user
        order.confirmed_at = timezone.now()
        order.save()
        # Đây là mốc "hàng thực sự rời kho" — với công ty Thương mại, mỗi dòng gắn Hàng hoá (product)
        # tạo 1 dòng Xuất kho tương ứng. Đơn giản hoá: lấy kho ĐẦU TIÊN đang hoạt động của công ty
        # (chưa hỗ trợ chọn kho cụ thể lúc lên đơn — nếu cần nhiều kho một lúc, làm sau khi thấy nhu cầu).
        warehouse = Warehouse.objects.filter(company=order.company, is_active=True).first()
        if warehouse is not None:
            StockMovement.objects.bulk_create(
                StockMovement(
                    product=item.product,
                    warehouse=warehouse,
                    movement_type=StockMovement.MovementType.OUT,
                    quantity=item.quantity,
                    reference_order_item=item,
                    created_by=request.user,
                )
                for item in order.items.all()
                if item.product is not None
            )
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["get"], url_path="label")
    def label(self, request, pk=None):
        # Import ở đây cùng lý do với PDF báo giá — weasyprint cần thư viện hệ thống chỉ có trên
        # server Linux lúc deploy, import ở module-level sẽ làm cả app không chạy nổi trên máy dev.
        from weasyprint import HTML

        order = self.get_object()
        order_code = f"{order.company.code}-{order.id:06d}"

        qr_buf = io.BytesIO()
        qrcode.make(order_code).save(qr_buf, format="PNG")
        qr_data_uri = "data:image/png;base64," + base64.b64encode(qr_buf.getvalue()).decode()

        html = render_to_string(
            "crm/order_label_pdf.html",
            {
                "order_code": order_code,
                "created_date": order.created_at.strftime("%d/%m/%Y"),
                "customer_name": order.customer.name,
                "contact_person": order.customer.contact_person,
                "phone": order.customer.phone,
                "pickup_point": order.pickup_point,
                "delivery_point": order.delivery_point,
                "items": [
                    {"description": item.description, "quantity": _format_qty_vn(item.quantity)}
                    for item in order.items.all()
                ],
                "weight_display": f"{_format_qty_vn(order.weight_kg)} kg" if order.weight_kg is not None else "",
                "cod_display": _format_money_vn(order.cod_amount) if order.cod_amount else "",
                "note": order.note,
                "company_name": order.company.legal_name or order.company.name,
                "hotline": order.company.hotline or settings.COMPANY_HOTLINE,
                "logo_data_uri": _company_logo_data_uri(order.company),
                "qr_data_uri": qr_data_uri,
            },
        )
        pdf_bytes = HTML(string=html).write_pdf()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{order_code}.pdf"'
        return response


class NoticeViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    """Thông báo nội bộ — ai cũng xem được, chỉ Quản lý được đăng/sửa/xoá."""

    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = self.get_active_company()
        # company=None nghĩa là thông báo cho TẤT CẢ công ty — luôn hiện, cộng với thông báo riêng
        # của đúng công ty đang chọn.
        return Notice.objects.select_related("created_by").filter(
            Q(company__isnull=True) | Q(company=company)
        )

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý mới đăng được thông báo nội bộ.")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DashboardStatsView(CompanyScopedMixin, APIView):
    """Số liệu tổng quan cho trang Dashboard — scope theo vai trò giống các ViewSet ở trên."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = self.get_active_company()
        orders = Order.objects.filter(company=company)
        acts = Activity.objects.filter(company=company).select_related("customer", "performed_by")
        # Partner không gắn công ty (hồ sơ dùng chung) — thu hẹp về đúng đối tác từng có đơn hàng với
        # công ty đang chọn, nếu không "tổng khách hàng" sẽ lẫn cả khách của công ty khác.
        partners = Partner.objects.filter(orders__company=company).distinct()
        if not is_manager(request.user):
            partners = partners.filter(assigned_to=request.user)
            orders = orders.filter(customer__assigned_to=request.user)
            acts = acts.filter(customer__assigned_to=request.user)

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = orders.filter(created_at__gte=month_start)

        recent_orders = orders.select_related("customer").order_by("-created_at")[:8]
        recent_activities = acts.order_by("-activity_at")[:8]
        activity = sorted(
            [
                {
                    "type": "order",
                    "at": o.created_at,
                    "text": f"Đơn hàng #{o.id} cho {o.customer.name}",
                }
                for o in recent_orders
            ]
            + [
                {
                    "type": "contact",
                    "at": a.activity_at,
                    "text": f"{a.get_activity_type_display()} — {a.customer.name}: {a.title[:80]}",
                }
                for a in recent_activities
            ],
            key=lambda item: item["at"],
            reverse=True,
        )[:8]

        return Response(
            {
                "total_customers": partners.count(),
                "new_customers_week": partners.filter(created_at__gte=week_ago).count(),
                "orders_this_month": orders_this_month.count(),
                "revenue_this_month": _sum_revenue(orders_this_month),
                "total_revenue_all_time": _sum_revenue(orders),
                "gross_profit_this_month": _sum_gross_profit(orders_this_month),
                "gross_profit_on_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=True)
                ),
                "gross_profit_off_platform_this_month": _sum_gross_profit(
                    orders_this_month.filter(on_platform=False)
                ),
                "recent_activity": activity,
            }
        )
