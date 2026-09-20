from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from crm.models import Order, OrderItem, Partner
from finance.models import OrderCost, OrderFinance, OrderPayment
from .funds import FUNDS, allocate, profit_bands, validate_policy
from .fund_views import period_bounds, report


class FundMathTests(SimpleTestCase):
    def test_both_columns_sum_to_100_and_all_children_reconcile(self):
        validate_policy()
        self.assertEqual(len(FUNDS), 13)
        def keys(nodes):
            return [key for n in nodes for key in [n["key"], *keys(n["children"])]]
        self.assertEqual(len(keys(FUNDS)), len(set(keys(FUNDS))))

    def test_image_top_level_percentages(self):
        expected = [(20, 53), (10, 4), (8, "3.2"), (15, 6), (3, "1.2"), (2, ".8"),
                    (3, "1.2"), (3, "1.2"), (2, ".8"), (2, ".8"), (3, "1.2"), (4, "1.6"), (25, 25)]
        self.assertEqual([(n["below_pct"], n["above_pct"]) for n in FUNDS],
                         [(Decimal(a), Decimal(b)) for a, b in expected])

    def test_bad_hierarchy_fails_instead_of_double_counting(self):
        broken = deepcopy(FUNDS)
        broken[0]["children"][0]["below_pct"] = Decimal(2)
        with self.assertRaises(ValueError):
            validate_policy(broken)

    def test_actual_floor_and_historic_comparison_are_different(self):
        args = [Decimal(n) for n in (12000000, 10000000, 8000000)]
        self.assertEqual(profit_bands(*args), (Decimal(2000000), Decimal(2000000)))
        self.assertEqual(profit_bands(*args, "historical_75_25"), (Decimal(3000000), Decimal(1000000)))
        with self.assertRaises(ValueError):
            profit_bands(*args, "unknown")

    def test_floor_boundaries_and_loss_are_not_silently_clamped(self):
        for revenue, floor, cost, expected in [(10, 10, 8, (2, 0)), (9, 10, 8, (2, -1)), (7, 10, 8, (2, -3)), (12, 10, 11, (-1, 2))]:
            self.assertEqual(profit_bands(Decimal(revenue), Decimal(floor), Decimal(cost)), tuple(map(Decimal, expected)))

    def test_example_sales_total_and_reserve_are_distinct(self):
        rows = allocate(Decimal(2000000), Decimal(2000000))
        self.assertEqual(rows[0]["amount"], "1460000")
        self.assertEqual(rows[0]["children"][-1]["amount"], "322000")
        self.assertEqual(rows[1]["amount"], "280000")
        self.assertEqual(rows[2]["amount"], "224000")
        self.assertEqual(rows[-1]["amount"], "1000000")

    def test_exact_allocation_reconciles_even_with_fractional_inputs(self):
        for below, above in [("0", "0"), (".01", ".03"), ("123456.1234", "8.9999"), ("99999999999999.12", "8121231.9232")]:
            result = allocate(Decimal(below), Decimal(above))
            def reconcile(nodes):
                for item in nodes:
                    self.assertEqual(Decimal(item["amount"]), Decimal(item["below_amount"]) + Decimal(item["above_amount"]))
                    if item["children"]:
                        self.assertEqual(Decimal(item["amount"]), sum(Decimal(child["amount"]) for child in item["children"]))
                        reconcile(item["children"])
            reconcile(result)
            self.assertEqual(sum(Decimal(r["amount"]) for r in result), Decimal(below) + Decimal(above))

    def test_period_validation_and_december_boundary(self):
        start, end = period_bounds("2025-12")
        self.assertEqual(start.month, 12)
        self.assertEqual(end.year, 2026)
        for bad in ["", "2026-1", "2026-13", "9999-12", "0000-01", "2026-09-01"]:
            with self.assertRaises(Exception):
                period_bounds(bad)


@override_settings(COMPANY_HUB_ENABLED=True, COMPANY_HUB_OWNER_USERNAME="fund-owner")
class FundApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("fund-owner", is_superuser=True, is_staff=True)
        self.other = User.objects.create_user("fund-other", is_superuser=True, is_staff=True)
        self.company, _ = Company.objects.get_or_create(code="CAVI", defaults={"name": "CAVI", "business_type": "transport"})
        self.other_company, _ = Company.objects.get_or_create(code="LIVI", defaults={"name": "LIVI", "business_type": "trading"})
        self.customer = Partner.objects.create(name="Khách minh họa kiểm thử", assigned_to=self.owner.profile)
        self.customer.companies.add(self.company)
        self.order = Order.objects.create(company=self.company, customer=self.customer, status="done", floor_price=10000000)
        self.item = OrderItem.objects.create(order=self.order, description="Dịch vụ giả", quantity=1, unit_price=12000000, unit_cost=8000000)
        self.finance = OrderFinance.objects.get(order=self.order)
        now = timezone.now()
        self.finance.revenue_amount = 12000000
        self.finance.revenue_recorded_at = now
        self.finance.settled_at = now
        self.finance.save()
        self.payment = OrderPayment.objects.create(finance=self.finance, payment_type="collection", amount=12000000)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.pk)}

    def get(self, **params):
        return self.client.get("/api/company-hub/funds/", params, **self.headers)

    def test_live_summary_and_detail_no_posting(self):
        res = self.get()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total"], "4000000")
        self.assertEqual(res.data["calculated_count"], 1)
        self.assertFalse(res.data["posted"])
        self.assertIsNone(res.data["cash_balance"])
        self.assertEqual(res.data["policy"]["status"], "needs_confirmation")
        self.assertIn("no-store", res["Cache-Control"])
        detail = self.get(fund="sales").data
        self.assertEqual(detail["detail"]["amount"], "1460000")
        row = detail["rows"]["results"][0]
        self.assertEqual(row["order_id"], self.order.pk)
        self.assertEqual(row["finance_id"], self.finance.pk)
        self.assertEqual(row["customer_id"], self.customer.pk)
        self.assertEqual(row["allocation"]["amount"], "1460000")

    def test_new_cost_updates_amount_without_accumulating_again(self):
        self.assertEqual(self.get().data["total"], "4000000")
        cost = OrderCost.objects.create(finance=self.finance, category="other", amount=100000)
        self.assertEqual(self.get().data["total"], "3900000")
        self.assertEqual(self.get().data["total"], "3900000")
        cost.amount = 200000
        cost.save()
        self.assertEqual(self.get().data["total"], "3800000")

    def test_nested_reserve_and_commission_have_their_own_contribution_detail(self):
        for key, amount in [("sales_reserve", "322000"), ("sales_assistant", "150000"), ("sales_admin", "250000")]:
            response = self.get(fund=key)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["detail"]["amount"], amount)
            self.assertEqual(response.data["rows"]["results"][0]["allocation"]["amount"], amount)

    def test_cod_does_not_count_as_service_revenue(self):
        self.payment.payment_type = "cod"
        self.payment.save()
        res = self.get().data
        self.assertEqual(res["calculated_count"], 0)
        self.assertEqual(res["rows"]["results"][0]["receipt_total"], "0")

    def test_refund_or_underpayment_removes_projection_until_reconciled(self):
        OrderPayment.objects.create(finance=self.finance, payment_type="refund", amount=1)
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_overpayment_is_held_for_review_not_added_as_profit(self):
        OrderPayment.objects.create(finance=self.finance, payment_type="collection", amount=1)
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_explicit_zero_revenue_never_falls_back_to_order_total(self):
        self.finance.revenue_amount = 0
        self.finance.save()
        row = self.get().data["rows"]["results"][0]
        self.assertEqual(row["revenue"], "0")
        self.assertEqual(row["status"], "waiting")

    def test_missing_cost_not_a_free_service(self):
        self.item.unit_cost = 0
        self.item.save()
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_missing_floor_not_inferred_from_current_catalog(self):
        self.order.floor_price = None
        self.order.save()
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_unsettled_or_unrecorded_orders_wait(self):
        self.finance.settled_at = None
        self.finance.save()
        self.assertEqual(self.get().data["calculated_count"], 0)
        self.finance.settled_at = timezone.now()
        self.finance.revenue_recorded_at = None
        self.finance.save()
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_cancelled_and_incomplete_orders_do_not_contribute(self):
        for state in ["cancelled", "pending_receipt"]:
            self.order.status = state
            self.order.save()
            self.assertEqual(self.get().data["calculated_count"], 0)

    def test_negative_band_is_preserved_but_not_posted_or_clamped(self):
        self.item.unit_cost = 11000000
        self.item.save()
        res = self.get().data
        row = res["rows"]["results"][0]
        self.assertEqual(row["below"], "-1000000")
        self.assertEqual(row["above"], "2000000")
        self.assertEqual(row["status"], "review")
        self.assertEqual(res["total"], "0")
        self.assertEqual(res["waiting_count"], 1)

    def test_foreign_currency_and_future_receipt_are_not_assumed(self):
        self.finance.currency = "USD"
        self.finance.save()
        self.assertEqual(self.get().data["calculated_count"], 0)
        self.finance.currency = "VND"
        self.finance.save()
        self.payment.paid_at = timezone.now() + timedelta(days=1)
        self.payment.save()
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_mixed_cost_currency_is_not_guessed(self):
        OrderCost.objects.create(finance=self.finance, category="other", amount=1, currency="USD")
        self.assertEqual(self.get().data["calculated_count"], 0)

    def test_scope_no_other_company_or_copied_admin(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.get().status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.get().status_code, [401, 403])
        self.client.force_authenticate(self.owner)
        self.headers = {"HTTP_X_COMPANY_ID": str(self.other_company.pk)}
        self.assertEqual(self.get().status_code, 400)
        self.headers = {}
        self.assertEqual(self.get().status_code, 400)

    def test_example_uses_no_real_ids_or_database_writes(self):
        counts = (Order.objects.count(), OrderPayment.objects.count(), OrderCost.objects.count())
        sample = self.get(example="1", fund="sales").data
        self.assertTrue(sample["is_example"])
        self.assertIsNone(sample["rows"]["results"][0]["order_id"])
        self.assertEqual(sample["detail"]["amount"], "1460000")
        self.assertEqual(counts, (Order.objects.count(), OrderPayment.objects.count(), OrderCost.objects.count()))
        self.assertEqual(self.get(example="1", method="historical_75_25").data["funds"][0]["amount"], "1130000")

    def test_bad_parameters_and_write_methods_rejected(self):
        for params in [{"period": "bad"}, {"fund": "unknown"}, {"method": "bad"}, {"example": "yes"}, {"page": "0"}]:
            self.assertEqual(self.get(**params).status_code, 400)
        for method in [self.client.post, self.client.patch, self.client.delete]:
            self.assertEqual(method("/api/company-hub/funds/", {}, **self.headers).status_code, 405)

    @override_settings(COMPANY_HUB_ENABLED=False)
    def test_disabled_feature_denies_access(self):
        self.assertEqual(self.get().status_code, 403)

    def test_month_uses_completion_not_old_creation(self):
        previous = timezone.now() - timedelta(days=65)
        Order.objects.filter(pk=self.order.pk).update(created_at=previous)
        self.assertEqual(self.get().data["calculated_count"], 1)
        self.assertEqual(self.get(period=previous.strftime("%Y-%m")).data["calculated_count"], 0)

    def test_detail_pagination_keeps_whole_period_total(self):
        prototype = self.get().data["rows"]["results"][0]
        result = report([prototype] * 21, "floor", "sales", 2)
        self.assertEqual(result["detail"]["amount"], "30660000")
        self.assertEqual(len(result["rows"]["results"]), 1)
