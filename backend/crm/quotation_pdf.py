"""Atlas TEST quotation. Render only explicit customer-facing fields, in memory.

No ORM writes, templates supplied by users, remote images, or inferred terms.
The legacy staff renderer remains in views.py until release approval.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import RLock
import unicodedata
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, LongTable, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

INK = colors.HexColor("#18372d")
MUTED = colors.HexColor("#5e7067")
EMERALD = colors.HexColor("#186a49")
NIGHT = colors.HexColor("#102f25")
LIME = colors.HexColor("#d8eaa2")
LINE = colors.HexColor("#e0e7e1")
WASH = colors.HexColor("#f4f5f1")
WHITE = colors.white
MARGIN = 42
WIDTH = A4[0] - 2 * MARGIN
_RENDER_LOCK = RLock()  # ReportLab font registration/subsetting is process-global.


class QuotationPDFError(ValueError):
    """An actionable input error, never a silent truncated quotation."""


@dataclass(frozen=True)
class QuoteLine:
    name: str
    unit: str
    quantity: Decimal
    price: Decimal

    @property
    def total(self):
        with localcontext() as context:
            context.prec = 40
            return self.quantity * self.price


@dataclass(frozen=True)
class QuoteDocument:
    reference: str
    inquiry_reference: str
    date: str
    brand: str
    company_name: str
    company_address: str
    company_phone: str
    company_tax_code: str
    customer_name: str
    customer_contact: str
    customer_phone: str
    customer_address: str
    note: str
    lines: tuple[QuoteLine, ...]
    state: str = "ĐÃ LƯU"
    sample: bool = False
    logo: bytes = b""

    @property
    def total(self):
        with localcontext() as context:
            context.prec = 40
            return sum((line.total for line in self.lines), Decimal("0"))


def display_number(value):
    """Vietnamese grouping, exact decimals; never round a displayed quote silently."""
    number = Decimal(value)
    if not number.is_finite():
        raise QuotationPDFError("Báo giá có số liệu không hợp lệ. Vui lòng kiểm tra lại.")
    whole, _, fraction = format(number, ",f").partition(".")
    fraction = fraction.rstrip("0")
    return whole.replace(",", ".") + ("," + fraction if fraction else "")


def _text(value):
    # NFC combines Vietnamese accents. PDF paragraphs are plain text, never markup.
    value = unicodedata.normalize("NFC", str(value or ""))
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = value.translate(str.maketrans({char: "-" for char in "‐‑‒–—−"}))
    return "".join(char for char in value if char == "\n" or unicodedata.category(char) not in {"Cc", "Cf"})


def _uploaded_logo(company):
    # No default CAVI logo for another company; no URL passed to ReportLab/Pillow.
    if not company.logo:
        return b""
    try:
        with company.logo.open("rb") as stream:
            content = stream.read(2_000_001)
        return content if len(content) <= 2_000_000 else b""
    except (OSError, ValueError):
        return b""


def bundled_cavi_logo():
    """Existing CAVI brand asset, not a generated or third-party replacement."""
    try:
        with (Path(__file__).parent / "static" / "crm" / "logo.jpg").open("rb") as stream:
            content = stream.read(2_000_001)
        return content if len(content) <= 2_000_000 else b""
    except OSError:
        return b""


def quotation_logo(company):
    uploaded = _uploaded_logo(company)
    if uploaded:
        return uploaded
    # Only the canonical CAVI company gets this fallback; LIVI/AVI keep their identity.
    return bundled_cavi_logo() if company.code == "CAVI" else b""


def document_from_quotation(quotation):
    company, customer = quotation.inquiry.company, quotation.inquiry.customer
    saved = quotation.saved_at
    date = saved or quotation.updated_at
    if timezone.is_aware(date):
        date = timezone.localtime(date)
    state = "ĐÃ LƯU" if saved else "BẢN NHÁP - CHƯA LƯU"
    if quotation.pending_approval_id and quotation.pending_approval.status == "pending":
        state = "ĐANG CÓ ĐỀ XUẤT CHỜ DUYỆT"
    # pending_snapshot and all inquiry cost/floor/ceiling fields are deliberately absent.
    lines = tuple(QuoteLine(line.item_name, line.unit, line.quantity, line.price)
                  for line in quotation.lines.all()[:501])
    return QuoteDocument(
        reference=f"BG-{quotation.pk:06d}", inquiry_reference=f"HG-{quotation.inquiry_id:06d}",
        date=date.strftime("%d/%m/%Y"), brand=company.name,
        company_name=company.legal_name or company.name,
        company_address=company.address, company_phone=company.hotline,
        company_tax_code=company.tax_code, customer_name=customer.name,
        customer_contact=customer.contact_person, customer_phone=customer.phone,
        customer_address=customer.address, note=quotation.note, lines=lines,
        state=state, logo=quotation_logo(company),
    )


@lru_cache(maxsize=1)
def _fonts():
    directory = Path(__file__).with_name("pdf_fonts")
    for name, filename in (("Atlas", "NotoSans-Regular.ttf"), ("AtlasBold", "NotoSans-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily("Atlas", normal="Atlas", bold="AtlasBold")


def _paragraph(value, size=9, color=INK, bold=False, align=0, after=0, keep=False):
    return Paragraph(escape(_text(value)).replace("\n", "<br/>"), ParagraphStyle(
        "atlas", fontName="AtlasBold" if bold else "Atlas", fontSize=size,
        leading=size * 1.5, textColor=color, alignment=align, spaceAfter=after,
        splitLongWords=True, allowWidows=0, allowOrphans=0, keepWithNext=keep,
    ))


def _money_cell(value, width, bold=False):
    text = display_number(value)
    font = "AtlasBold" if bold else "Atlas"
    # Large valid Decimal values remain whole and exact, rather than clipping columns.
    size = min(9, (width - 14) / max(pdfmetrics.stringWidth(text, font, 1), 1))
    if size < 6.5:
        raise QuotationPDFError("Giá trị quá dài để trình bày rõ trên A4. Vui lòng kiểm tra báo giá.")
    return _paragraph(text, size=size, bold=bold, align=TA_RIGHT)


def _logo_flowable(data):
    if not data:
        return None
    # Reject huge or non-raster images, and strip EXIF/metadata before embedding.
    from PIL import Image as PILImage, UnidentifiedImageError
    try:
        with PILImage.open(BytesIO(data)) as source:
            if source.format not in {"PNG", "JPEG"} or source.width * source.height > 4_000_000:
                return None
            source.load()
            clean = source.convert("RGBA")
            clean.thumbnail((600, 240))
            buffer = BytesIO()
            clean.save(buffer, format="PNG")
            scale = min(112 / clean.width, 68 / clean.height)
            return Image(BytesIO(buffer.getvalue()), width=clean.width * scale, height=clean.height * scale)
    except (OSError, ValueError, UnidentifiedImageError, PILImage.DecompressionBombError):
        return None


class _PageCanvas(Canvas):
    """Replay pages once to add accurate page totals; no temporary customer files."""
    def __init__(self, *args, quote, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []
        self.quote = quote

    def showPage(self):
        if len(self._pages) >= 50:
            raise QuotationPDFError("Báo giá vượt 50 trang. Vui lòng chia thành các báo giá nhỏ hơn.")
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        pages = self._pages
        for state in pages:
            self.__dict__.update(state)
            self.saveState()
            self.setStrokeColor(LINE)
            self.setLineWidth(0.6)
            self.line(MARGIN, 48, A4[0] - MARGIN, 48)
            self.setFont("Atlas", 7)
            self.setFillColor(MUTED)
            self.drawString(MARGIN, 56, "Báo giá không phải hóa đơn hoặc xác nhận khách đã đồng ý.")
            self.drawString(MARGIN, 33, f"{self.quote.reference}  /  BẢN TEST - KHÔNG GỬI KHÁCH")
            self.drawRightString(A4[0] - MARGIN, 33, f"Trang {self._pageNumber} / {len(pages)}")
            self.restoreState()
            Canvas.showPage(self)
        Canvas.save(self)


def _page_header(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(EMERALD)
    canvas.rect(MARGIN, A4[1] - 22, 30, 3, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(MARGIN + 34, A4[1] - 22, 12, 3, fill=1, stroke=0)
    canvas.setFont("Atlas", 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(A4[0] - MARGIN, A4[1] - 22, "BÁO GIÁ  /  QUOTATION")
    canvas.restoreState()


def _story(quote):
    story = []
    logo = _logo_flowable(quote.logo)
    company_details = [_paragraph(quote.company_name, size=10 if logo else 9, bold=True, after=3)]
    for value in (quote.company_address, "Hotline: " + quote.company_phone if quote.company_phone else "",
                  "MST: " + quote.company_tax_code if quote.company_tax_code else ""):
        if value:
            company_details.append(_paragraph(value, size=8, color=MUTED))
    if logo:
        logo.hAlign = "LEFT"
        header = Table([[logo, company_details]], colWidths=[104, WIDTH - 104], hAlign="LEFT")
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header)
    else:
        story.append(_paragraph(quote.brand, size=22, bold=True, color=EMERALD, after=2))
        story.extend(company_details)
    story.extend([Spacer(1, 22), _paragraph("Báo giá", size=32, bold=True, after=4)])
    story.append(_paragraph("DỮ LIỆU MINH HỌA - KHÔNG PHẢI BÁO GIÁ THỰC TẾ" if quote.sample
                            else "BẢN TEST - KHÔNG GỬI KHÁCH", size=8, color=EMERALD, bold=True, after=16))

    recipient = [_paragraph("KÍNH GỬI", size=7, color=MUTED, bold=True, after=5),
                 _paragraph(quote.customer_name, size=12, bold=True, after=5)]
    recipient.extend(_paragraph(v, size=8.5, color=MUTED) for v in (
        quote.customer_contact, quote.customer_phone, quote.customer_address) if v)
    metadata = [_paragraph("THÔNG TIN BÁO GIÁ", size=7, color=MUTED, bold=True, after=5),
                _paragraph(quote.reference, size=12, bold=True, after=5),
                _paragraph("Ngày lưu: " + quote.date if quote.state == "ĐÃ LƯU" else "Ngày bản ghi: " + quote.date, size=8.5),
                _paragraph("Hỏi giá: " + quote.inquiry_reference, size=8.5),
                _paragraph(quote.state, size=7, color=EMERALD, bold=True)]
    details = Table([[recipient, metadata]], colWidths=[WIDTH * .61, WIDTH * .39], hAlign="LEFT")
    details.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WASH), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.extend([details, Spacer(1, 22), CondPageBreak(90),
                  _paragraph("01  /  Chi tiết báo giá", size=11, bold=True, after=10)])
    widths = [24, WIDTH - 24 - 50 - 54 - 90 - 112, 50, 54, 90, 112]
    headers = ["STT", "Hạng mục / dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"]
    rows = [[_paragraph(title, size=7, color=MUTED, bold=True, align=TA_RIGHT if i >= 3 else 0)
             for i, title in enumerate(headers)]]
    for index, line in enumerate(quote.lines, 1):
        rows.append([_paragraph(str(index).zfill(2), size=7, color=MUTED),
                     _paragraph(line.name or "Chưa nhập tên hạng mục", bold=True),
                     _paragraph(line.unit or "-", size=8),
                     _money_cell(line.quantity, widths[3]), _money_cell(line.price, widths[4]),
                     _money_cell(line.total, widths[5], bold=True)])
    if not quote.lines:
        rows.append(["", _paragraph("Chưa có hạng mục báo giá.", color=MUTED), "", "", "", ""])
    table = LongTable(rows, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 1, EMERALD),
        ("LINEBELOW", (0, 1), (-1, -1), .45, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#fafbf9")]),
    ]))
    story.extend([table, Spacer(1, 14)])

    total_label = [_paragraph("TỔNG GIÁ TRỊ BÁO GIÁ", size=8, color=LIME, bold=True),
                   _paragraph(f"{len(quote.lines)} hạng mục  /  Đồng Việt Nam (VND)", size=7, color=WHITE)]
    total_text = display_number(quote.total) + " VND"
    total_size = min(18, (WIDTH * .56 - 28) / max(pdfmetrics.stringWidth(total_text, "AtlasBold", 1), 1))
    total = Table([[total_label, _paragraph(total_text, size=total_size, bold=True,
                                            color=WHITE, align=TA_RIGHT)]], colWidths=[WIDTH * .44, WIDTH * .56])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NIGHT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 16), ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(KeepTogether([total, Spacer(1, 7), _paragraph(
        "Tổng bằng số lượng × đơn giá của các dòng báo giá. Không tự cộng thuế hoặc phụ phí ngoài báo giá.",
        size=7, color=MUTED)]))
    if quote.note.strip():
        story.extend([Spacer(1, 20), CondPageBreak(70),
                      _paragraph("02  /  Nội dung & ghi chú", size=11, bold=True, after=8),
                      _paragraph(quote.note, size=9)])
    if quote.state != "ĐÃ LƯU":
        story.extend([Spacer(1, 12), _paragraph(
            "Bản nháp chưa lưu." if "CHƯA LƯU" in quote.state else
            "Đang có đề xuất chờ duyệt. PDF chỉ thể hiện nội dung bản ghi hiện tại, không lấy nội dung đề xuất.",
            size=8, color=EMERALD, bold=True)])
    return story


def render_quotation_pdf(quote):
    if len(quote.lines) > 500 or len(quote.note) > 30_000:
        raise QuotationPDFError("Báo giá quá dài để xuất PDF. Vui lòng chia nhỏ nội dung.")
    if any(len(line.name) > 2000 or not line.quantity.is_finite() or not line.price.is_finite()
           for line in quote.lines):
        raise QuotationPDFError("Hạng mục báo giá không hợp lệ. Vui lòng kiểm tra lại.")
    with _RENDER_LOCK:
        _fonts()
        # Fail clearly for unsupported scripts/emoji instead of generating missing-glyph boxes.
        source_text = " ".join(str(value) for value in quote.__dict__.values() if isinstance(value, str))
        source_text += " ".join(line.name + " " + line.unit for line in quote.lines)
        charset = pdfmetrics.getFont("Atlas").face.charToGlyph
        if any(ord(char) not in charset for char in _text(source_text) if not char.isspace()):
            raise QuotationPDFError("Báo giá có ký tự ngoài bộ chữ hỗ trợ. Vui lòng bỏ biểu tượng emoji hoặc dùng tiếng Việt/Latin.")
        stream = BytesIO()
        doc = BaseDocTemplate(stream, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                              topMargin=42, bottomMargin=66, title=f"Báo giá {quote.reference} - TEST",
                              author=_text(quote.company_name), pageCompression=1, lang="vi-VN")
        frame = Frame(MARGIN, 66, WIDTH, A4[1] - 108, leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        doc.addPageTemplates(PageTemplate(id="Atlas", frames=frame, onPage=_page_header))
        doc.build(_story(quote), canvasmaker=lambda *a, **kw: _PageCanvas(*a, quote=quote, **kw))
        return stream.getvalue()
