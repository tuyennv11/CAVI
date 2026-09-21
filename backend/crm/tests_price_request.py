from decimal import Decimal

from django.test import TestCase

from companies.models import Company
from inventory.models import Lot, LotCost, Product, StockMovement, Warehouse

from .models import (
    Partner,
    PriceRequest,
    PriceRequestItem,
    PurchaseRequest,
    PurchaseRequestAllocation,
    PurchaseRequestItem,
)
from .services.price_request import refresh_source_status


class SourceStatusTests(TestCase):
    """Test 3 mục 31 — đúng 3 ví dụ số liệu ở mục 6 tài liệu nghiệp vụ (đủ hàng/không có hàng/có
    nhưng không đủ)."""

    def setUp(self):
        self.company = Company.objects.create(code="SRC-TEST", name="Synthetic source co", business_type="trading")
        self.warehouse = Warehouse.objects.create(company=self.company, name="Synthetic PP warehouse")
        self.product = Product.objects.create(company=self.company, sku="SRC-SKU", name="Synthetic goods")
        self.partner = Partner.objects.create(name="Synthetic customer", is_customer=True)
        self.price_request = PriceRequest.objects.create(customer=self.partner, company=self.company)

    def _stock(self, quantity):
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="in", quantity=Decimal(quantity)
        )

    def test_case_a_du_hang_trong_kho(self):
        self._stock(10000)
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, product=self.product, item_name="Goods", quantity=Decimal("3000")
        )
        refresh_source_status(item)
        item.refresh_from_db()
        self.assertEqual(item.source_status, PriceRequestItem.SourceStatus.TON_KHO)

    def test_case_b_khong_co_hang(self):
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, product=self.product, item_name="Goods", quantity=Decimal("3000")
        )
        refresh_source_status(item)
        item.refresh_from_db()
        self.assertEqual(item.source_status, PriceRequestItem.SourceStatus.MUA_MOI)

    def test_case_c_co_hang_nhung_khong_du(self):
        self._stock(7000)
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, product=self.product, item_name="Goods", quantity=Decimal("8000")
        )
        refresh_source_status(item)
        item.refresh_from_db()
        self.assertEqual(item.source_status, PriceRequestItem.SourceStatus.TON_KHO_VA_MUA_BO_SUNG)

    def test_case_d_chua_xac_dinh_hang_hoa(self):
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, item_name="Chưa rõ sản phẩm", quantity=Decimal("100")
        )
        refresh_source_status(item)
        item.refresh_from_db()
        self.assertEqual(item.source_status, PriceRequestItem.SourceStatus.CHUA_XAC_DINH)


class PurchaseRequestAllocationTests(TestCase):
    """Test 4 mục 31 — 1 lần mua phục vụ nhiều Yêu cầu giá cùng lúc, đúng ví dụ mục 7 tài liệu."""

    def test_allocation_across_multiple_price_requests_sums_correctly(self):
        company = Company.objects.create(code="ALLOC-TEST", name="Synthetic allocation co", business_type="trading")
        partner_a = Partner.objects.create(name="Khach A", is_customer=True)
        partner_b = Partner.objects.create(name="Khach B", is_customer=True)
        request_a = PriceRequest.objects.create(customer=partner_a, company=company)
        request_b = PriceRequest.objects.create(customer=partner_b, company=company)
        item_a = PriceRequestItem.objects.create(price_request=request_a, item_name="Goods", quantity=Decimal("1000"))
        item_b = PriceRequestItem.objects.create(price_request=request_b, item_name="Goods", quantity=Decimal("2000"))

        purchase_request = PurchaseRequest.objects.create(purchase_type="theo_don_khach")
        purchase_item = PurchaseRequestItem.objects.create(
            purchase_request=purchase_request, item_name="Goods", quantity=Decimal("5000")
        )
        PurchaseRequestAllocation.objects.create(
            purchase_request_item=purchase_item, price_request_item=item_a, quantity_allocated=Decimal("1000")
        )
        PurchaseRequestAllocation.objects.create(
            purchase_request_item=purchase_item, price_request_item=item_b, quantity_allocated=Decimal("2000")
        )
        # 2.000 còn lại đưa vào kho — không gắn price_request_item nào (để trống).
        PurchaseRequestAllocation.objects.create(
            purchase_request_item=purchase_item, price_request_item=None, quantity_allocated=Decimal("2000")
        )

        allocations = purchase_item.allocations.all()
        total_allocated = sum((a.quantity_allocated for a in allocations), Decimal("0"))
        self.assertEqual(total_allocated, purchase_item.quantity)
        self.assertEqual(allocations.filter(price_request_item=item_a).first().quantity_allocated, Decimal("1000"))
        self.assertEqual(allocations.filter(price_request_item=item_b).first().quantity_allocated, Decimal("2000"))
        self.assertEqual(allocations.filter(price_request_item__isnull=True).count(), 1)


class LotCostTests(TestCase):
    """Test 5 mục 31 — công thức giá vốn lô đúng ví dụ mục 13 tài liệu (quy đổi sang VNĐ theo quyết
    định đã chốt: chi phí lô hàng chỉ tính bằng VNĐ, không cần tỷ giá)."""

    def test_unit_cost_matches_worked_example(self):
        company = Company.objects.create(code="LOT-TEST", name="Synthetic lot co", business_type="trading")
        warehouse = Warehouse.objects.create(company=company, name="Synthetic PP warehouse")
        product = Product.objects.create(company=company, sku="LOT-SKU", name="Synthetic goods")
        lot = Lot.objects.create(
            product=product, warehouse=warehouse, quantity=Decimal("10000"), unit_price=Decimal("10")
        )
        LotCost.objects.create(lot=lot, category="hang_hoa", amount=Decimal("100000"))
        LotCost.objects.create(lot=lot, category="van_chuyen", amount=Decimal("15000"))
        LotCost.objects.create(lot=lot, category="hai_quan", amount=Decimal("3000"))
        LotCost.objects.create(lot=lot, category="khac", amount=Decimal("2000"))

        self.assertEqual(lot.total_cost, Decimal("120000"))
        self.assertEqual(lot.unit_cost, Decimal("12"))
