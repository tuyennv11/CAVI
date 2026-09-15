"""Navigation is read-only and never grants the destination's missing permissions."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from companies.models import Company
from crm.models import Activity, Order, OrderItem, Partner, PriceInquiry, Quotation
from crm.serializers import OrderItemSerializer, QuotationSerializer
from hr.models import Profile
from inventory.models import Product, StockMovement, Warehouse
from inventory.serializers import StockMovementSerializer
from ops.models import Shipment, ShipmentBatch


class RecordNavigationTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(code="NAV-A", name="Synthetic navigation A", business_type="trading")
        self.b = Company.objects.create(code="NAV-B", name="Synthetic navigation B", business_type="transport")
        users = get_user_model().objects
        self.manager = users.create_user("synthetic-nav-manager", is_staff=True)
        self.member = users.create_user("synthetic-nav-member")
        self.peer = users.create_user("synthetic-nav-peer")
        self.other = users.create_user("synthetic-nav-other")
        self.member.profile.companies.add(self.a)
        self.peer.profile.companies.add(self.a)
        self.other.profile.companies.add(self.b)
        self.partner = Partner.objects.create(name="Synthetic customer", assigned_to=self.member)
        self.partner.companies.add(self.a)
        self.activity = Activity.objects.create(company=self.a, customer=self.partner, activity_type="call", title="Synthetic activity", assigned_to=self.member)
        self.client = APIClient()
        self.as_user(self.member)

    def as_user(self, user, company=None):
        self.client.force_authenticate(user)
        self.client.credentials(HTTP_X_COMPANY_ID=str((company or self.a).pk))

    def test_user_resolution_uses_profile_pk_not_user_pk_and_does_not_write(self):
        # Deliberately different IDs, as copied databases need not have matching sequences.
        Profile.objects.filter(user=self.member).delete()
        profile = Profile.objects.create(id=98765, user=self.member)
        profile.companies.add(self.a)
        self.member.refresh_from_db()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f"/api/hr/employees/by-user/{self.member.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"id": 98765})
        self.assertIn("no-store", response["Cache-Control"])
        for query in queries:
            self.assertFalse(query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")), query["sql"])

    def test_user_resolver_denies_peer_and_cross_company_even_for_manager(self):
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.peer.pk}/").status_code, 404)
        self.as_user(self.manager)
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.peer.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.other.pk}/").status_code, 404)
        self.as_user(self.member, self.b)
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.other.pk}/").status_code, 403)

    def test_missing_profile_is_not_created_on_get(self):
        Profile.objects.filter(user=self.peer).delete()
        self.as_user(self.manager)
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.peer.pk}/").status_code, 404)
        self.assertFalse(Profile.objects.filter(user=self.peer).exists())

    def test_activity_detail_reuses_assignment_and_company_scope(self):
        url = f"/api/activities/{self.activity.pk}/"
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer"], self.partner.pk)
        self.assertTrue(all(not q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for q in queries))
        self.as_user(self.peer)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.as_user(self.manager, self.b)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.as_user(None)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_link_relation_ids_are_explicit_and_read_only(self):
        inquiry = PriceInquiry.objects.create(customer=self.partner, company=self.a)
        quote = Quotation.objects.create(inquiry=inquiry)
        product = Product.objects.create(company=self.a, sku="SYN-NAV-P", name="Synthetic product")
        order = Order.objects.create(company=self.a, customer=self.partner)
        item = OrderItem.objects.create(order=order, product=product, description="Synthetic item")
        warehouse = Warehouse.objects.create(company=self.a, name="Synthetic warehouse")
        movement = StockMovement.objects.create(product=product, warehouse=warehouse, movement_type="out", quantity=1, reference_order_item=item)
        self.assertEqual(QuotationSerializer(quote).data["customer_id"], self.partner.pk)
        self.assertEqual(OrderItemSerializer(item).data["product"], product.pk)
        self.assertEqual(StockMovementSerializer(movement).data["reference_order"], order.pk)
        serializer = OrderItemSerializer(item, data={"product": 777}, partial=True)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("product", serializer.validated_data)
        self.assertTrue(QuotationSerializer().fields["customer_id"].read_only)
        self.assertTrue(StockMovementSerializer().fields["reference_order"].read_only)

    def test_existing_detail_routes_deny_cross_company(self):
        order = Order.objects.create(company=self.a, customer=self.partner)
        inquiry = PriceInquiry.objects.create(company=self.a, customer=self.partner)
        batch = ShipmentBatch.objects.create(company=self.a, route="Synthetic route")
        shipment = Shipment.objects.create(company=self.a, partner=self.partner, batch=batch, description="Synthetic shipment")
        product = Product.objects.create(company=self.a, sku="SYN-NAV-P", name="Synthetic product")
        warehouse = Warehouse.objects.create(company=self.a, name="Synthetic warehouse")
        paths = [("orders", order), ("price-inquiries", inquiry), ("shipments", shipment), ("shipment-batches", batch), ("products", product), ("warehouses", warehouse)]
        for resource, obj in paths:
            with self.subTest(resource=resource):
                self.as_user(self.manager)
                self.assertEqual(self.client.get(f"/api/{resource}/{obj.pk}/").status_code, 200)
                self.as_user(self.manager, self.b)
                self.assertEqual(self.client.get(f"/api/{resource}/{obj.pk}/").status_code, 404)

    def test_resolver_requires_login_and_rejects_malformed_identifiers(self):
        self.as_user(None)
        self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{self.member.pk}/").status_code, 401)
        self.as_user(self.manager)
        for value in ("0", "-1", "abc", "1.2"):
            self.assertEqual(self.client.get(f"/api/hr/employees/by-user/{value}/").status_code, 404)
