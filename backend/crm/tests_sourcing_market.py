from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from companies.models import Company
from .models import CostQuote, CostQuoteItem, Partner, PriceRequest, PriceRequestItem, SourcingPlan
from .services.sourcing import comparison_key, freight_total


class SourcingMarketTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.manager = users.create_user("market-manager", is_staff=True)
        self.supply = users.create_user("market-supply")
        self.other = users.create_user("market-other")
        self.sales = users.create_user("market-sales")
        group, _ = Group.objects.get_or_create(name=settings.GROUP_SUPPLY)
        self.supply.groups.add(group)
        self.other.groups.add(group)
        self.company = Company.objects.create(code="MARKET", name="Market", business_type="trading")
        for user in [self.supply, self.other, self.sales]:
            user.profile.companies.add(self.company)
        partner = Partner.objects.create(name="Customer", is_customer=True, assigned_to=self.sales.profile)
        pr = PriceRequest.objects.create(customer=partner, company=self.company, assigned_to=self.sales.profile, street_address="Delivery A")
        self.item = PriceRequestItem.objects.create(price_request=pr, item_name="Goods", quantity=2, unit="box")
        self.client = APIClient()
        self.client.credentials(HTTP_X_COMPANY_ID=str(self.company.id))
        self.client.force_authenticate(self.supply)
        self.until = str(timezone.localdate() + timedelta(days=7))

    def payload(self, **changes):
        data = {"price_request_item": self.item.id, "supplier_name": "NCC A", "carrier_name": "Carrier A",
            "confirmed": True, "valid_until": self.until, "available_at": str(timezone.localdate()),
            "tax_basis": "included", "payment_terms": "Paid on delivery", "delivery_terms": "Door to door in 2 days",
            "street_address": "Pickup A", "shipping_rate": "100", "shipping_rate_basis": "total",
            "items": [{"item_name": "Goods", "quantity": "2", "unit": "box", "unit_cost": "500",
                       "unit_length_cm": "100", "unit_width_cm": "100", "unit_height_cm": "100", "unit_weight_kg": "10"}]}
        data.update(changes)
        return data

    def quote(self, **changes):
        response = self.client.post("/api/cost-quotes/", self.payload(**changes), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def freight(self, q, **changes):
        data = {"goods_quote": q["id"], "carrier_name": "Carrier B", "rate": "2", "basis": "kg", "confirmed": True,
                "valid_until": self.until, "tax_basis": "included", "delivery_days": 2, "terms": "Door to door"}
        data.update(changes)
        return self.client.post("/api/freight-offers/", data, format="json")

    def propose(self, q, freight=None):
        return self.client.post("/api/sourcing-plans/", {"price_request_item": self.item.id,
            "goods_quote": q["id"], "freight_offer": freight, "reason": "Best suitable offer"}, format="json")

    def test_shared_answers_visible_to_another_supplier(self):
        q = self.quote()
        self.client.force_authenticate(self.other)
        response = self.client.get(f"/api/price-inquiry-items/{self.item.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cost_quotes"][0]["id"], q["id"])
        self.assertEqual(response.data["cost_quotes"][0]["market"]["goods_total"], "1000.0000")

    def test_revision_retains_original_rows(self):
        q = self.quote()
        revised = self.quote(supersedes=q["id"], shipping_rate="50")
        original = CostQuote.objects.get(pk=q["id"])
        self.assertFalse(original.active)
        self.assertEqual(original.shipping_rate, Decimal("100"))
        self.assertEqual(original.items.count(), 1)
        self.assertEqual(revised["supersedes"], original.id)

    def test_other_supplier_cannot_revise_or_withdraw(self):
        q = self.quote()
        self.client.force_authenticate(self.other)
        response = self.client.post("/api/cost-quotes/", self.payload(supersedes=q["id"]), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post(f"/api/cost-quotes/{q['id']}/withdraw/").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/cost-quotes/{q['id']}/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/cost-quotes/{q['id']}/").status_code, 405)

    def test_freight_independent_supplier_and_calculation(self):
        q = self.quote()
        self.client.force_authenticate(self.other)
        response = self.freight(q)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Decimal(response.data["total_cost"]), Decimal("40"))
        plan = self.propose(q, response.data["id"])
        self.assertEqual(plan.status_code, 201, plan.data)
        self.assertEqual(Decimal(plan.data["snapshot"]["landed_total"]), Decimal("1040"))

    def test_cannot_mix_freight_from_another_source(self):
        q1, q2 = self.quote(), self.quote(street_address="Pickup B")
        f = self.freight(q1)
        self.assertEqual(self.propose(q2, f.data["id"]).status_code, 400)

    def test_missing_shipping_is_not_free(self):
        q = self.quote(shipping_rate=None)
        self.assertIsNone(q["market"]["shipping_total"])
        self.assertEqual(self.propose(q).status_code, 400)

    def test_zero_shipping_is_valid(self):
        q = self.quote(shipping_rate="0")
        self.assertEqual(Decimal(q["shipping_cost"]), 0)
        self.assertEqual(self.propose(q).status_code, 201)

    def test_client_cannot_forge_snapshot_or_status(self):
        q = self.quote(active=False, delivery_snapshot="Forged destination")
        self.assertTrue(q["active"])
        self.assertEqual(q["delivery_snapshot"], "Delivery A")
        response = self.client.post("/api/sourcing-plans/", {"price_request_item": self.item.id,
            "goods_quote": q["id"], "reason": "test", "status": "approved", "snapshot": {"landed_total": "1"}}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "proposed")
        self.assertEqual(Decimal(response.data["snapshot"]["landed_total"]), 1100)

    def test_freight_revision_and_approved_freight_protection(self):
        q = self.quote()
        old = self.freight(q).data
        revised = self.freight(q, supersedes=old["id"], rate="1")
        self.assertEqual(revised.status_code, 201, revised.data)
        self.assertFalse(self.client.get(f"/api/freight-offers/{old['id']}/").data["active"])
        plan = self.propose(q, revised.data["id"])
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f"/api/sourcing-plans/{plan.data['id']}/approve/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/freight-offers/{revised.data['id']}/withdraw/").status_code, 400)

    def test_approving_one_rejects_other_proposals(self):
        q = self.quote()
        first, second = self.propose(q), self.propose(q)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f"/api/sourcing-plans/{first.data['id']}/approve/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/sourcing-plans/{second.data['id']}/approve/").status_code, 400)
        self.assertEqual(SourcingPlan.objects.filter(status="approved").count(), 1)

    def test_missing_weight_not_partially_summed(self):
        q = self.quote(shipping_rate_basis="kg")
        obj = CostQuote.objects.get(pk=q["id"])
        CostQuoteItem.objects.create(cost_quote=obj, item_name="Missing", quantity=1, unit="box", unit_cost=100)
        self.assertIsNone(freight_total(obj, Decimal("2"), "kg"))

    def test_expired_unconfirmed_unknown_tax_block_selection(self):
        for changes in [{"valid_until": str(timezone.localdate() - timedelta(days=1))}, {"confirmed": False}, {"tax_basis": "unknown"}]:
            q = self.quote(**changes)
            self.assertEqual(self.propose(q).status_code, 400)

    def test_manager_approval_and_selected_offer_protection(self):
        q = self.quote()
        plan = self.propose(q)
        self.assertEqual(plan.status_code, 201, plan.data)
        path = f"/api/sourcing-plans/{plan.data['id']}/approve/"
        self.assertEqual(self.client.post(path).status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertEqual(self.client.post(f"/api/cost-quotes/{q['id']}/withdraw/").status_code, 400)
        better = self.quote(shipping_rate="20")
        self.assertEqual(self.propose(better).status_code, 400)
        self.assertEqual(SourcingPlan.objects.get(pk=plan.data["id"]).goods_quote_id, q["id"])

    def test_changed_delivery_blocks_approval(self):
        q = self.quote()
        plan = self.propose(q)
        pr = self.item.price_request
        pr.street_address = "Delivery changed"
        pr.save()
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f"/api/sourcing-plans/{plan.data['id']}/approve/").status_code, 400)

    def test_withdraw_after_proposal_blocks_approval(self):
        q = self.quote()
        plan = self.propose(q)
        self.client.post(f"/api/cost-quotes/{q['id']}/withdraw/")
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f"/api/sourcing-plans/{plan.data['id']}/approve/").status_code, 400)

    def test_comparison_separates_quantity_and_tax(self):
        q1 = self.quote()
        p = self.payload()
        p["items"][0]["quantity"] = "3"
        q2 = self.quote(items=p["items"])
        self.assertNotEqual(q1["market"]["comparison_key"], q2["market"]["comparison_key"])
        obj = CostQuote.objects.get(pk=q1["id"])
        obj.tax_basis = "unknown"
        self.assertIsNone(comparison_key(obj))

    def test_company_isolation_on_read_and_create(self):
        other_company = Company.objects.create(code="OTHER", name="Other", business_type="trading")
        pr = PriceRequest.objects.create(customer=self.item.price_request.customer, company=other_company)
        foreign_item = PriceRequestItem.objects.create(price_request=pr, item_name="Foreign")
        foreign_quote = CostQuote.objects.create(price_request_item=foreign_item)
        self.assertEqual(self.client.get(f"/api/cost-quotes/{foreign_quote.id}/").status_code, 404)
        response = self.client.post("/api/cost-quotes/", self.payload(price_request_item=foreign_item.id), format="json")
        self.assertEqual(response.status_code, 403)
        response = self.freight({"id": foreign_quote.id})
        self.assertEqual(response.status_code, 403)

    def test_sales_cannot_submit_supplier_price(self):
        self.client.force_authenticate(self.sales)
        self.assertEqual(self.client.post("/api/cost-quotes/", self.payload(), format="json").status_code, 403)

    def test_negative_price_and_empty_rows_rejected(self):
        self.assertEqual(self.client.post("/api/cost-quotes/", self.payload(items=[]), format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/cost-quotes/", self.payload(shipping_rate="-1"), format="json").status_code, 400)

    def test_same_method_goods_bid_keeps_route_and_cargo(self):
        q = self.quote()
        self.client.force_authenticate(self.other)
        response = self.client.post(f"/api/cost-quotes/{q['id']}/bid-goods/", {
            "prices": ["450"], "supplier_name": "NCC B", "confirmed": True, "valid_until": self.until,
            "street_address": "Wrong pickup", "items": [], "shipping_rate": "0",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["based_on"], q["id"])
        self.assertEqual(response.data["street_address"], "Pickup A")
        self.assertEqual(response.data["items"][0]["quantity"], q["items"][0]["quantity"])
        self.assertEqual(Decimal(response.data["market"]["goods_total"]), Decimal("900"))
        self.assertIsNone(response.data["market"]["shipping_total"])
        self.assertEqual(response.data["market"]["comparison_key"], q["market"]["comparison_key"])
        self.assertTrue(CostQuote.objects.get(pk=q["id"]).active)

    def test_same_method_bid_rejects_invalid_price_and_withdrawn_source(self):
        q = self.quote()
        path = f"/api/cost-quotes/{q['id']}/bid-goods/"
        for prices in [[], [None], ["-1"], ["abc"]]:
            self.assertEqual(self.client.post(path, {"prices": prices}, format="json").status_code, 400)
        self.client.post(f"/api/cost-quotes/{q['id']}/withdraw/")
        self.assertEqual(self.client.post(path, {"prices": ["100"]}, format="json").status_code, 400)

    def test_comparison_separates_different_routes(self):
        a = self.quote()
        b = self.quote(street_address="Pickup B")
        self.assertNotEqual(a["market"]["comparison_key"], b["market"]["comparison_key"])

    def test_sales_cannot_bid_goods(self):
        q = self.quote()
        self.client.force_authenticate(self.sales)
        response = self.client.post(f"/api/cost-quotes/{q['id']}/bid-goods/", {"prices": ["100"]}, format="json")
        self.assertEqual(response.status_code, 403)
