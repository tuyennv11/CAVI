from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(ROOT_URLCONF="config.preview_urls")
class PreviewDataAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = get_user_model().objects.create_user(username="preview-owner", is_superuser=True, is_staff=True)
        self.staff = get_user_model().objects.create_user(username="preview-staff", is_staff=True)

    def test_requires_app_login(self):
        self.assertEqual(self.client.get("/preview/data/api/").status_code, 401)

    def test_regular_staff_cannot_read_cross_company_data(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/preview/data/api/").status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/preview/data/state/").status_code, 302)

    def test_owner_can_read_allowlisted_tables_without_caching(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/preview/data/api/?table=crm.order")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["table"], "crm.order")
        self.assertIn("no-store", response["Cache-Control"])

    def test_auth_table_and_writes_are_rejected(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/preview/data/api/?table=auth.user").status_code, 400)
        self.assertEqual(self.client.post("/preview/data/api/", {}).status_code, 405)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_viewer_is_not_mounted_in_production(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/preview/data/api/").status_code, 404)
