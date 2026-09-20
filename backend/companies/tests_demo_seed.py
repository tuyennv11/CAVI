from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import Notice, Order, OrderItem, Partner, PriceListItem, Task
from finance.models import OrderCost, OrderFinance, OrderPayment

from .demo_seed import COMPANY_CODE, OTHER_COMPANY_CODE, SEED_USERS, require_isolated_staging_database
from .models import Company


class TestDatabaseGuardTests(SimpleTestCase):
    @override_settings(SETTINGS_MODULE="config.staging_settings", CAVI_ENVIRONMENT="preview", ROOT_URLCONF="config.staging_urls", DEBUG=False)
    def test_requires_exact_database_and_actual_connection_identity(self):
        expected = {"ENGINE": "django.db.backends.postgresql", "NAME": "cavi_test", "USER": "cavi_test", "HOST": "test-db", "PORT": "5432"}
        with patch("companies.demo_seed.connection") as database:
            database.settings_dict = expected
            cursor = database.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("cavi_test", "cavi_test")
            require_isolated_staging_database()
            cursor.execute.assert_called_once_with("SELECT current_database(), current_user")
            cursor.fetchone.return_value = ("crm", "postgres")
            with self.assertRaises(CommandError):
                require_isolated_staging_database()
            for key in expected:
                database.settings_dict = {**expected, key: "wrong-target"}
                database.cursor.reset_mock()
                with self.subTest(key=key), self.assertRaises(CommandError):
                    require_isolated_staging_database()
                database.cursor.assert_not_called()

    @override_settings(SETTINGS_MODULE="config.staging_settings", CAVI_ENVIRONMENT="preview", ROOT_URLCONF="config.staging_urls", DEBUG=False)
    def test_production_local_preview_and_missing_confirmation_stop_before_db_access(self):
        for config in ({"SETTINGS_MODULE": "config.settings"}, {"SETTINGS_MODULE": "config.preview_settings"}, {"CAVI_ENVIRONMENT": "production"}, {"ROOT_URLCONF": "config.urls"}, {"DEBUG": True}):
            with override_settings(**config), patch("companies.demo_seed.connection") as database:
                database.settings_dict = {"ENGINE": "django.db.backends.postgresql", "NAME": "cavi_test", "USER": "cavi_test", "HOST": "test-db", "PORT": "5432"}
                with self.subTest(config=config), self.assertRaises(CommandError):
                    require_isolated_staging_database()
                database.cursor.assert_not_called()
        with patch("companies.management.commands.seed_test_data.seed_synthetic_data") as seed:
            with self.assertRaises(CommandError):
                call_command("seed_test_data", stdout=StringIO())
            seed.assert_not_called()


class SyntheticFixtureTests(TestCase):
    def seed(self):
        # Real DB identity validation is tested separately above. The mutation
        # below runs only on Django's temporary SQLite test DB, never .preview.
        with patch("companies.demo_seed.require_isolated_staging_database"):
            call_command("seed_test_data", confirm_isolated_test_database=True, stdout=StringIO())

    def test_creates_fake_scenarios_without_passwords_contacts_or_uploads(self):
        original_catalogue = list(PriceListItem.objects.values())
        self.seed()
        self.assertEqual(list(PriceListItem.objects.values()), original_catalogue)
        users = get_user_model().objects.all()
        self.assertEqual(users.count(), 5)
        self.assertEqual(set(users.values_list("username", flat=True)), set(SEED_USERS))
        for user in users:
            self.assertFalse(user.has_usable_password())
            self.assertEqual(user.email, "")
            self.assertEqual(user.profile.id_number, "")
            self.assertEqual(user.profile.phone, "")
            self.assertFalse(user.profile.avatar)
        self.assertEqual(Order.objects.count(), 5)
        self.assertEqual(OrderItem.objects.count(), 5)
        self.assertEqual(OrderFinance.objects.count(), 5)
        self.assertEqual(Partner.objects.count(), 3)
        self.assertEqual(Task.objects.count(), 7)
        self.assertEqual(Notice.objects.count(), 2)
        for order in Order.objects.all():
            self.assertTrue(order.description.startswith("[TEST]"))
            self.assertFalse(order.image)
        for partner in Partner.objects.all():
            self.assertEqual(partner.phone, "")
            self.assertEqual(partner.contact_person, "")
        task = Task.objects.get(title="[TEST] Duyệt cách hiển thị phiếu nhận hàng")
        self.assertEqual(timezone.localtime(task.due_at).date(), timezone.localdate())

    def test_rerun_preserves_owner_edits_password_and_due_dates_without_duplicates(self):
        self.seed()
        task = Task.objects.first()
        task.title = "Owner edited this fixture"
        task.status = Task.Status.DONE
        task.save()
        user = get_user_model().objects.get(username=SEED_USERS[1])
        user.set_password("ephemeral-test-only-not-a-real-password")
        user.save()
        password = user.password
        self.seed()
        task.refresh_from_db()
        user.refresh_from_db()
        self.assertEqual(task.title, "Owner edited this fixture")
        self.assertEqual(task.status, Task.Status.DONE)
        self.assertEqual(user.password, password)
        self.assertEqual(Task.objects.count(), 7)
        self.assertEqual(Order.objects.count(), 5)

    def test_refuses_database_with_existing_user_instead_of_renaming_or_promoting_them(self):
        original = get_user_model().objects.create_user(username=SEED_USERS[0])
        with self.assertRaises(CommandError):
            self.seed()
        original.refresh_from_db()
        self.assertFalse(original.is_superuser)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(Company.objects.filter(code=COMPANY_CODE).exists())
        self.assertEqual(Order.objects.count(), 0)

    def test_refuses_existing_business_or_company_collision(self):
        Partner.objects.create(name="Existing company data")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Partner.objects.count(), 1)
        self.assertEqual(get_user_model().objects.count(), 0)
        Company.objects.create(code=COMPANY_CODE, name="An existing unrelated company", business_type="transport")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(Company.objects.filter(code=OTHER_COMPANY_CODE).exists())

    def test_partial_failure_rolls_back_only_this_seed_transaction(self):
        company_count = Company.objects.count()
        with patch("companies.demo_seed.Notice.objects.create", side_effect=RuntimeError("simulated failure")):
            with self.assertRaises(RuntimeError):
                self.seed()
        self.assertEqual(Company.objects.count(), company_count)
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Task.objects.count(), 0)

    def test_refuses_database_with_existing_price_list_item(self):
        PriceListItem.objects.create(
            company=Company.objects.get(code="LIVI"), category=PriceListItem.Category.I,
            group_name="Nhóm thử", group_code="TEST", item_code="TEST-001", name="Dịch vụ thử",
        )
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(get_user_model().objects.count(), 0)


@override_settings(ROOT_URLCONF="config.staging_urls")
class SyntheticAppPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with patch("companies.demo_seed.require_isolated_staging_database"):
            call_command("seed_test_data", confirm_isolated_test_database=True, stdout=StringIO())
        cls.company = Company.objects.get(code=COMPANY_CODE)
        cls.other = Company.objects.get(code=OTHER_COMPANY_CODE)
        cls.owner = get_user_model().objects.get(username=SEED_USERS[0])
        cls.sales = get_user_model().objects.get(username=SEED_USERS[1])
        cls.colleague = get_user_model().objects.get(username=SEED_USERS[2])
        cls.accountant = get_user_model().objects.get(username=SEED_USERS[3])

    def setUp(self):
        self.client = APIClient()
        self.headers = {"HTTP_X_COMPANY_ID": str(self.company.pk)}

    def rows(self, response):
        self.assertEqual(response.status_code, 200)
        return response.data["results"] if isinstance(response.data, dict) else response.data

    def test_sales_sees_only_assigned_customers_and_orders(self):
        self.client.force_authenticate(self.sales)
        partners = self.rows(self.client.get("/api/partners/", **self.headers))
        self.assertEqual({row["id"] for row in partners}, set(Partner.objects.filter(assigned_to=self.sales.profile).values_list("id", flat=True)))
        orders = self.rows(self.client.get("/api/orders/", **self.headers))
        self.assertEqual(len(orders), 3)
        colleague_order = Order.objects.get(created_by=self.colleague)
        self.assertEqual(self.client.get(f"/api/orders/{colleague_order.pk}/", **self.headers).status_code, 404)

    def test_changing_company_header_cannot_escape_membership(self):
        self.client.force_authenticate(self.sales)
        for route in ("partners", "orders", "tasks", "orders/pending-receipt"):
            with self.subTest(route=route):
                response = self.client.get(f"/api/{route}/", HTTP_X_COMPANY_ID=str(self.other.pk))
                self.assertEqual(response.status_code, 403)

    def test_tasks_hide_colleague_and_other_company_work(self):
        self.client.force_authenticate(self.sales)
        tasks = self.rows(self.client.get("/api/tasks/", **self.headers))
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(row["assigned_to"] == self.sales.pk for row in tasks))

    def test_owner_still_uses_selected_company_for_orders(self):
        self.client.force_authenticate(self.owner)
        rows = self.rows(self.client.get("/api/orders/", **self.headers))
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(self.rows(self.client.get("/api/orders/", HTTP_X_COMPANY_ID=str(self.other.pk)))), 1)
        self.assertEqual(self.client.get("/api/orders/").status_code, 400)

    def test_sales_cannot_read_finance_or_preview_database_viewer(self):
        self.client.force_authenticate(self.sales)
        self.assertEqual(self.client.get("/api/finance/orders/", **self.headers).status_code, 403)
        self.assertEqual(self.client.get("/preview/data/api/").status_code, 403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/preview/data/api/").status_code, 200)

    def test_accountant_cannot_pay_order_from_another_company(self):
        self.client.force_authenticate(self.accountant)
        self.assertEqual(len(self.rows(self.client.get("/api/finance/orders/", **self.headers))), 4)
        other_finance = OrderFinance.objects.get(order__company=self.other)
        previous = OrderPayment.objects.count()
        response = self.client.post("/api/finance/payments/", {"finance": other_finance.pk, "payment_type": "collection", "amount": "100000"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(OrderPayment.objects.count(), previous)
        self.assertEqual(self.client.get("/api/finance/orders/", HTTP_X_COMPANY_ID=str(self.other.pk)).status_code, 403)

    def test_cannot_create_order_for_unassigned_or_cross_company_customer(self):
        self.client.force_authenticate(self.sales)
        inaccessible = [Partner.objects.get(assigned_to=self.colleague.profile), Partner.objects.get(companies=self.other)]
        for partner in inaccessible:
            previous = Order.objects.count()
            response = self.client.post("/api/orders/", {"customer": partner.pk, "description": "Blocked fixture", "items": [{"description": "Sample", "quantity": "1", "unit_price": "100", "unit_cost": "50"}]}, format="json", **self.headers)
            self.assertIn(response.status_code, (400, 403))
            self.assertEqual(Order.objects.count(), previous)

    def test_valid_sales_order_and_manager_order_for_colleague_remain_available(self):
        for actor, customer in [(self.sales, Partner.objects.get(assigned_to=self.sales.profile)), (self.owner, Partner.objects.get(assigned_to=self.colleague.profile))]:
            self.client.force_authenticate(actor)
            response = self.client.post("/api/orders/", {"customer": customer.pk, "description": "[TEST] Valid sample", "items": [{"description": "Sample", "quantity": "1", "unit_price": "100", "unit_cost": "50"}]}, format="json", **self.headers)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Order.objects.get(pk=response.data["id"]).company_id, self.company.pk)

    def test_patch_cannot_reassign_an_existing_order_to_an_inaccessible_customer(self):
        self.client.force_authenticate(self.sales)
        order = Order.objects.filter(created_by=self.sales).first()
        customer_id = order.customer_id
        for customer in [Partner.objects.get(assigned_to=self.colleague.profile), Partner.objects.get(companies=self.other)]:
            response = self.client.patch(f"/api/orders/{order.pk}/", {"customer": customer.pk}, format="json", **self.headers)
            self.assertEqual(response.status_code, 400)
            order.refresh_from_db()
            self.assertEqual(order.customer_id, customer_id)

    def test_cannot_attach_supplier_from_other_company_to_finance_cost(self):
        self.client.force_authenticate(self.accountant)
        supplier = Partner.objects.get(companies=self.other)
        supplier.is_supplier = True
        supplier.save(update_fields=["is_supplier"])
        finance = OrderFinance.objects.filter(order__company=self.company).first()
        previous = finance.costs.count()
        response = self.client.post("/api/finance/costs/", {"finance": finance.pk, "supplier": supplier.pk, "category": "pickup", "amount": "100"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(finance.costs.count(), previous)

    def test_cost_accepts_own_company_supplier_but_patch_cannot_switch_to_other_company(self):
        self.client.force_authenticate(self.accountant)
        supplier = Partner.objects.get(assigned_to=self.sales.profile)
        supplier.is_supplier = True
        supplier.save(update_fields=["is_supplier"])
        finance = OrderFinance.objects.filter(order__company=self.company).first()
        response = self.client.post("/api/finance/costs/", {"finance": finance.pk, "supplier": supplier.pk, "category": "pickup", "amount": "100"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 201)
        cost = OrderCost.objects.get(pk=response.data["id"])
        other_supplier = Partner.objects.get(companies=self.other)
        other_supplier.is_supplier = True
        other_supplier.save(update_fields=["is_supplier"])
        response = self.client.patch(f"/api/finance/costs/{cost.pk}/", {"supplier": other_supplier.pk}, format="json", **self.headers)
        self.assertEqual(response.status_code, 400)
        cost.refresh_from_db()
        self.assertEqual(cost.supplier_id, supplier.pk)
