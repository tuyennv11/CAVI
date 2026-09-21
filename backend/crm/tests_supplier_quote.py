from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from companies.models import Company

from .models import (
    Partner,
    PriceRequest,
    PriceRequestItem,
    PurchaseRequest,
    PurchaseRequestAllocation,
    PurchaseRequestItem,
    SupplierQuote,
)


class LandedUnitCostTests(TestCase):
    def test_includes_shipping_cost_spread_over_quantity(self):
        item = PurchaseRequestItem.objects.create(
            purchase_request=PurchaseRequest.objects.create(purchase_type="theo_don_khach"),
            item_name="Goods", quantity=Decimal("10"),
        )
        supplier = Partner.objects.create(name="NCC test", is_supplier=True)
        quote = SupplierQuote.objects.create(
            purchase_request_item=item, supplier=supplier, unit_price=Decimal("90000"),
            quantity=Decimal("10"), shipping_cost=Decimal("30000"),
        )
        self.assertEqual(quote.landed_unit_cost, Decimal("93000"))

    def test_no_shipping_cost_falls_back_to_unit_price(self):
        item = PurchaseRequestItem.objects.create(
            purchase_request=PurchaseRequest.objects.create(purchase_type="theo_don_khach"),
            item_name="Goods", quantity=Decimal("10"),
        )
        supplier = Partner.objects.create(name="NCC test", is_supplier=True)
        quote = SupplierQuote.objects.create(
            purchase_request_item=item, supplier=supplier, unit_price=Decimal("100000"), quantity=Decimal("10"),
        )
        self.assertEqual(quote.landed_unit_cost, Decimal("100000"))


class SupplierQuoteBoardApiTests(TestCase):
    """Test luồng Sàn báo giá NCC: Cung ứng nhập báo giá, Kinh doanh phụ trách chọn giá — chọn giá
    không rẻ nhất bắt buộc phải giải thích, người không liên quan không xem/chọn được."""

    def setUp(self):
        users = get_user_model().objects
        self.sales = users.create_user("synthetic-sq-sales")
        self.supply = users.create_user("synthetic-sq-supply")
        self.outsider = users.create_user("synthetic-sq-outsider")
        supply_group, _ = Group.objects.get_or_create(name=settings.GROUP_SUPPLY)
        self.supply.groups.add(supply_group)
        # create-purchase-request đi qua PriceRequestItemViewSet (CompanyScopedMixin) — Cung ứng
        # không phải Quản lý nên get_active_company() bắt phải thuộc đúng 1 công ty.
        self.company = Company.objects.create(code="SQ-TEST", name="Synthetic supplier-quote co", business_type="trading")
        self.supply.profile.companies.add(self.company)

        self.customer = Partner.objects.create(name="Khach hang test", is_customer=True, assigned_to=self.sales.profile)
        self.supplier = Partner.objects.create(name="NCC test", is_supplier=True)
        self.price_request = PriceRequest.objects.create(
            customer=self.customer, assigned_to=self.sales.profile, company=self.company,
        )
        self.price_item = PriceRequestItem.objects.create(
            price_request=self.price_request, item_name="Ruou saam", quantity=Decimal("10"), unit="thung",
        )
        self.purchase_request = PurchaseRequest.objects.create(purchase_type="theo_don_khach")
        self.purchase_item = PurchaseRequestItem.objects.create(
            purchase_request=self.purchase_request, item_name="Ruou saam", quantity=Decimal("10"), unit="thung",
        )
        PurchaseRequestAllocation.objects.create(
            purchase_request_item=self.purchase_item, price_request_item=self.price_item, quantity_allocated=Decimal("10"),
        )
        self.cheap_quote = SupplierQuote.objects.create(
            purchase_request_item=self.purchase_item, supplier=self.supplier,
            unit_price=Decimal("90000"), quantity=Decimal("10"), shipping_cost=Decimal("30000"),
        )
        self.expensive_quote = SupplierQuote.objects.create(
            purchase_request_item=self.purchase_item, supplier=self.supplier,
            unit_price=Decimal("100000"), quantity=Decimal("10"), shipping_cost=Decimal("50000"),
        )
        self.client = APIClient()

    def test_outsider_cannot_see_or_select(self):
        self.client.force_authenticate(self.outsider)
        list_response = self.client.get("/api/purchase-request-items/")
        self.assertEqual(list_response.data["count"], 0)
        select_response = self.client.post(f"/api/supplier-quotes/{self.expensive_quote.id}/select/", {}, format="json")
        self.assertEqual(select_response.status_code, 404)

    def test_sales_selecting_non_cheapest_requires_note(self):
        self.client.force_authenticate(self.sales)
        without_note = self.client.post(
            f"/api/supplier-quotes/{self.expensive_quote.id}/select/", {}, format="json"
        )
        self.assertEqual(without_note.status_code, 400)

        with_note = self.client.post(
            f"/api/supplier-quotes/{self.expensive_quote.id}/select/",
            {"selection_note": "NCC nay giao nhanh hon"}, format="json",
        )
        self.assertEqual(with_note.status_code, 200)
        self.expensive_quote.refresh_from_db()
        self.cheap_quote.refresh_from_db()
        self.assertTrue(self.expensive_quote.is_selected)
        self.assertFalse(self.cheap_quote.is_selected)

    def test_sales_selecting_cheapest_does_not_require_note(self):
        self.client.force_authenticate(self.sales)
        response = self.client.post(
            f"/api/supplier-quotes/{self.cheap_quote.id}/select/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.cheap_quote.refresh_from_db()
        self.assertTrue(self.cheap_quote.is_selected)

    def test_supply_cannot_select_only_sales_or_manager_can(self):
        self.client.force_authenticate(self.supply)
        response = self.client.post(
            f"/api/supplier-quotes/{self.cheap_quote.id}/select/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_purchase_request_from_price_request_item_is_idempotent(self):
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, item_name="Hang moi", quantity=Decimal("5"), unit="cai",
        )
        self.client.force_authenticate(self.supply)
        first = self.client.post(f"/api/price-inquiry-items/{item.id}/create-purchase-request/")
        self.assertEqual(first.status_code, 201)
        second = self.client.post(f"/api/price-inquiry-items/{item.id}/create-purchase-request/")
        self.assertEqual(second.status_code, 400)

    def test_sales_cannot_create_purchase_request(self):
        item = PriceRequestItem.objects.create(
            price_request=self.price_request, item_name="Hang moi 2", quantity=Decimal("5"), unit="cai",
        )
        self.client.force_authenticate(self.sales)
        response = self.client.post(f"/api/price-inquiry-items/{item.id}/create-purchase-request/")
        self.assertEqual(response.status_code, 403)
