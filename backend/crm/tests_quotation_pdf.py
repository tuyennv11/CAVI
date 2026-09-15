"""Synthetic-only regression tests: decimal accuracy, layout, permissions, no writes."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from approvals.models import ApprovalRequest
from companies.models import Company
from crm.models import Partner, PriceInquiry, Quotation, QuotationLine
from crm.quotation_pdf import (
    QuoteDocument, QuoteLine, QuotationPDFError, _text,
    bundled_cavi_logo, display_number, document_from_quotation, quotation_logo, render_quotation_pdf,
)


def fixture():
    return QuoteDocument(
        reference="BG-TEST-123", inquiry_reference="HG-TEST-456", date="14/09/2026",
        brand="CAVI", company_name="Công ty mẫu", company_address="Địa chỉ mẫu",
        company_phone="", company_tax_code="", customer_name="Khách hàng mẫu",
        customer_contact="", customer_phone="", customer_address="",
        note="Nội dung đã lưu", sample=True,
        lines=(QuoteLine("Đóng kiện hàng hóa", "Kiện", Decimal("1.25"), Decimal("123.45")),),
    )


class QuotationPDFTests(SimpleTestCase):
    def test_bundled_logo_is_only_used_for_cavi(self):
        logo = bundled_cavi_logo()
        self.assertTrue(logo.startswith(b"\xff\xd8"))
        self.assertEqual(quotation_logo(SimpleNamespace(code="CAVI", logo=None)), logo)
        for code in ("LIVI", "AVI", "CAVI-TEST", "OTHER"):
            self.assertEqual(quotation_logo(SimpleNamespace(code=code, logo=None)), b"")

    def test_uploaded_logo_takes_precedence_over_cavi_fallback(self):
        with patch("crm.quotation_pdf._uploaded_logo", return_value=b"specific company logo"):
            self.assertEqual(quotation_logo(SimpleNamespace(code="CAVI")), b"specific company logo")

    def test_cavi_logo_is_embedded_and_preserves_aspect_ratio(self):
        from crm.quotation_pdf import _logo_flowable
        logo = bundled_cavi_logo()
        image = _logo_flowable(logo)
        self.assertIsNotNone(image)
        self.assertEqual(image.drawWidth, image.drawHeight)
        self.assertEqual(image.drawHeight, 68)
        pdf = render_quotation_pdf(replace(fixture(), logo=logo))
        self.assertIn(b"/Subtype /Image", pdf)
        self.assertIn(b"/FontFile2", pdf)

    def test_exact_decimal_totals_and_vietnamese_format(self):
        quote = fixture()
        self.assertEqual(quote.total, Decimal("154.3125"))
        self.assertEqual(display_number(quote.total), "154,3125")
        self.assertEqual(display_number(Decimal("1234567.80")), "1.234.567,8")
        self.assertEqual(display_number(Decimal("0.00")), "0")
        with self.assertRaises(QuotationPDFError):
            display_number(Decimal("NaN"))

    def test_pdf_contains_embedded_fonts_and_no_active_content(self):
        pdf = render_quotation_pdf(fixture())
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIn(b"/FontFile2", pdf)
        self.assertNotIn(b"/JavaScript", pdf)
        self.assertNotIn(b"/URI", pdf)

    def test_plain_text_cannot_inject_remote_images_or_links(self):
        quote = replace(fixture(), note='<img src="https://example.invalid/private"/> & <b>literal</b>')
        pdf = render_quotation_pdf(quote)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertNotIn(b"/Subtype /Image", pdf)
        self.assertNotIn(b"/URI", pdf)
        self.assertEqual(_text("Va\u0302\u0323n\u2011ta\u0309i\u202e"), "Vận-tải")

    def test_many_rows_repeat_header_and_summary_appears_once(self):
        # Text extraction is supplemented by Poppler visual QA outside the server test suite.
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest("Optional pypdf QA dependency is not installed")
        quote = replace(fixture(), lines=fixture().lines * 45)
        reader = PdfReader(BytesIO(render_quotation_pdf(quote)))
        texts = [page.extract_text() for page in reader.pages]
        self.assertGreater(len(texts), 1)
        self.assertEqual("\n".join(texts).count("TỔNG GIÁ TRỊ BÁO GIÁ"), 1)
        for i, text in enumerate(texts, 1):
            self.assertIn(f"Trang {i} / {len(texts)}", text)
            self.assertIn("KHÔNG GỬI KHÁCH", text)
        for text in texts[:-1]:
            self.assertIn("Thành tiền", text)
        self.assertIn("Đóng kiện hàng hóa", texts[0])

    def test_empty_quote_and_corrupt_logo_render_without_fabrication(self):
        self.assertTrue(render_quotation_pdf(replace(fixture(), lines=(), logo=b"invalid image")).startswith(b"%PDF"))

    def test_oversized_or_invalid_input_fails_without_truncation(self):
        for quote in (replace(fixture(), lines=fixture().lines * 501), replace(fixture(), note="x" * 30001),
                      replace(fixture(), note="Không xuất ô vuông: 🚚"),
                      replace(fixture(), lines=(QuoteLine("x", "", Decimal("NaN"), Decimal("1")),))):
            with self.subTest(quote_type=type(quote)):
                with self.assertRaises(QuotationPDFError):
                    render_quotation_pdf(quote)


@override_settings(CAVI_QUOTATION_PDF_ATLAS=True)
class QuotationPDFAPITests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(code="PDF-A", name="Synthetic PDF A", business_type="transport")
        self.b = Company.objects.create(code="PDF-B", name="Synthetic PDF B", business_type="trading")
        users = get_user_model().objects
        self.owner = users.create_user("synthetic-pdf-owner")
        self.peer = users.create_user("synthetic-pdf-peer")
        self.manager = users.create_user("synthetic-pdf-manager", is_staff=True)
        self.owner.profile.companies.add(self.a)
        self.peer.profile.companies.add(self.a)
        self.partner = Partner.objects.create(name="Synthetic client", assigned_to=self.owner, note="PRIVATE CRM NOTE")
        self.partner.companies.add(self.a)
        self.inquiry = PriceInquiry.objects.create(customer=self.partner, company=self.a, cost_price=333, floor_price=444)
        self.quote = Quotation.objects.create(inquiry=self.inquiry, note="Customer-facing note", saved_at=timezone.now())
        QuotationLine.objects.create(quotation=self.quote, item_name="Synthetic freight", quantity=Decimal("1.25"), price=Decimal("123.45"))
        self.client = APIClient()
        self.url = f"/api/quotations/{self.quote.pk}/pdf/"
        self.authenticate(self.owner)

    def authenticate(self, user, company=None):
        self.client.force_authenticate(user)
        self.client.credentials(HTTP_X_COMPANY_ID=str((company or self.a).pk))

    def test_export_is_authenticated_read_only_pdf_with_private_headers(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("bao-gia-test-", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))
        for query in queries:
            self.assertFalse(query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")), query["sql"])

    def test_peer_cross_company_and_anonymous_cannot_render(self):
        with patch("crm.quotation_pdf.render_quotation_pdf") as render:
            self.authenticate(self.peer)
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.authenticate(self.manager, self.b)
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.authenticate(None)
            self.assertEqual(self.client.get(self.url).status_code, 401)
            render.assert_not_called()

    def test_snapshot_internal_fields_and_cross_brand_defaults_never_enter_document(self):
        approval = ApprovalRequest.objects.create(company=self.a, title="Synthetic approval", requested_by=self.owner,
                                                  request_type="proposal", status="pending")
        self.quote.pending_approval = approval
        self.quote.pending_snapshot = {"note": "PRIVATE PENDING", "lines": [{"price": 987654321}]}
        self.quote.save()
        document = document_from_quotation(self.quote)
        self.assertEqual(document.note, "Customer-facing note")
        self.assertEqual(document.total, Decimal("154.3125"))
        self.assertEqual(document.state, "ĐANG CÓ ĐỀ XUẤT CHỜ DUYỆT")
        self.assertEqual(document.company_phone, "")
        self.assertEqual(document.logo, b"")
        self.assertNotIn("PRIVATE", repr(document))
        self.assertNotIn("floor_price", document.__dataclass_fields__)

    def test_staff_flag_off_keeps_original_template_and_renderer(self):
        from types import SimpleNamespace
        fake_html = SimpleNamespace(write_pdf=lambda: b"%PDF-legacy")
        with override_settings(CAVI_QUOTATION_PDF_ATLAS=False), patch.dict("sys.modules", {
            "weasyprint": SimpleNamespace(HTML=lambda **kw: fake_html)
        }), patch("crm.views.render_to_string", return_value="legacy") as template, patch("crm.quotation_pdf.render_quotation_pdf") as atlas:
            response = self.client.get(self.url)
        self.assertEqual(response.content, b"%PDF-legacy")
        self.assertEqual(template.call_args.args[0], "crm/quotation_pdf.html")
        atlas.assert_not_called()

    def test_validation_errors_are_actionable_not_server_errors(self):
        with patch("crm.quotation_pdf.render_quotation_pdf", side_effect=QuotationPDFError("Nội dung quá dài")):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nội dung quá dài", str(response.data))
