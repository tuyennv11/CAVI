from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from crm.models import Order, OrderItem, Partner

from .models import OrderCost, OrderFinance, OrderPayment, next_monday_noon


class FinancePolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="finance-test")
        self.company = Company.objects.create(name="CAVI Test", code="CVT", business_type="transport")
        self.partner = Partner.objects.create(name="Khách thử nghiệm", assigned_to=self.user)
        self.partner.companies.add(self.company)
        self.order = Order.objects.create(customer=self.partner, company=self.company, created_by=self.user)
        OrderItem.objects.create(
            order=self.order,
            description="Vận chuyển HCM - Phnom Penh",
            quantity=2,
            unit_price=Decimal("500"),
            unit_cost=Decimal("300"),
        )
        self.finance = OrderFinance.objects.get(order=self.order)

    def test_finance_totals_debt_and_pickup_deposit(self):
        OrderCost.objects.create(
            finance=self.finance,
            category=OrderCost.Category.PICKUP,
            amount=Decimal("100"),
        )
        OrderPayment.objects.create(
            finance=self.finance,
            payment_type=OrderPayment.PaymentType.COLLECTION,
            amount=Decimal("400"),
        )
        self.assertEqual(self.finance.effective_revenue, Decimal("1000"))
        self.assertEqual(self.finance.total_cost, Decimal("700"))
        self.assertEqual(self.finance.debt_amount, Decimal("600"))
        self.assertEqual(self.finance.recommended_deposit, Decimal("50"))

    def test_contract_and_credit_policy(self):
        self.finance.cargo_value = Decimal("5000")
        self.finance.cargo_value_currency = OrderFinance.Currency.USD
        self.finance.revenue_amount = Decimal("50000000")
        self.finance.currency = OrderFinance.Currency.VND
        self.finance.exchange_rate_to_vnd = Decimal("1")
        self.finance.usd_exchange_rate_vnd = Decimal("25000")
        self.finance.credit_terms_days = 15
        self.assertTrue(self.finance.contract_required_by_policy)
        self.assertEqual(self.finance.credit_approval_level, "sales_manager")

    def test_settlement_deadline_is_next_monday_noon(self):
        zone = ZoneInfo("Asia/Ho_Chi_Minh")
        friday = datetime(2026, 9, 11, 16, 30, tzinfo=zone)
        monday = datetime(2026, 9, 14, 8, 0, tzinfo=zone)
        self.assertEqual(next_monday_noon(friday), datetime(2026, 9, 14, 12, 0, tzinfo=zone))
        self.assertEqual(next_monday_noon(monday), datetime(2026, 9, 21, 12, 0, tzinfo=zone))

    def test_finance_deadlines_follow_completed_order(self):
        self.order.status = Order.Status.DONE
        self.order.save(update_fields=["status", "updated_at"])
        self.finance.refresh_from_db()
        self.assertIsNotNone(self.finance.completed_at)
        self.assertIsNotNone(self.finance.settlement_due_at)
        local_due = timezone.localtime(self.finance.settlement_due_at)
        self.assertEqual(local_due.weekday(), 0)
        self.assertEqual(local_due.hour, 12)

    def test_record_revenue_button_reaches_api_without_allowing_duplicate_finance(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        client = APIClient()
        client.force_authenticate(user=self.user)
        headers = {"HTTP_X_COMPANY_ID": str(self.company.pk)}
        response = client.post(f"/api/finance/orders/{self.finance.pk}/record-revenue/", **headers)
        self.assertEqual(response.status_code, 200)
        self.finance.refresh_from_db()
        self.assertEqual(self.finance.revenue_recorded_by, self.user)
        self.assertEqual(client.post("/api/finance/orders/", {}, **headers).status_code, 405)
