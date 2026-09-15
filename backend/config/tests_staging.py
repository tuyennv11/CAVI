import os
import runpy
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings

from .staging_config import staging_config
from .staging_views import environment, health


class StagingIsolationTests(SimpleTestCase):
    def setUp(self):
        # Fixtures only. Not generated credentials and never written to any env file.
        self.env = {
            "CAVI_TEST_ORIGIN": "https://staging.cavi.vn",
            "CAVI_TEST_SECRET_KEY": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "CAVI_TEST_DB_PASSWORD": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            "CAVI_TEST_ISOLATION_CONFIRMED": "true",
            "CAVI_TEST_RELEASE_ID": "test-20260914-001",
        }

    def test_valid_config_is_explicit_and_normalized(self):
        result = staging_config({**self.env, "CAVI_TEST_ORIGIN": "https://STAGING.cavi.vn/"})
        self.assertEqual(result["origin"], "https://staging.cavi.vn")
        self.assertEqual(result["release"], "test-20260914-001")

    def test_never_falls_back_to_local_or_production(self):
        for origin in ("", "http://staging.cavi.vn", "https://app.vantaiduongbo.net", "https://APP.vantaiduongbo.net./", "https://vantaiduongbo.net", "https://165.22.55.145", "https://localhost", "https://mac.local", "https://api.example.com", "https://test.invalid", "https://u:p@staging.cavi.vn", "https://staging.cavi.vn/api", "https://staging.cavi.vn?secret=x", "https://staging.cavi.vn#fragment", "https://staging.cavi.vn:444"):
            with self.subTest(origin=origin), self.assertRaises(ImproperlyConfigured):
                staging_config({**self.env, "CAVI_TEST_ORIGIN": origin})

    def test_credentials_must_be_separate_and_not_examples(self):
        for changes in ({"CAVI_TEST_SECRET_KEY": ""}, {"CAVI_TEST_DB_PASSWORD": ""}, {"CAVI_TEST_SECRET_KEY": "x" * 60}, {"CAVI_TEST_DB_PASSWORD": "replace-with-your-own-password-1234567890"}, {"DJANGO_SECRET_KEY": self.env["CAVI_TEST_SECRET_KEY"]}, {"POSTGRES_PASSWORD": self.env["CAVI_TEST_DB_PASSWORD"]}, {"CAVI_TEST_DB_PASSWORD": self.env["CAVI_TEST_SECRET_KEY"]}):
            with self.subTest(changes=list(changes)), self.assertRaises(ImproperlyConfigured):
                staging_config({**self.env, **changes})

    def test_requires_isolation_and_specific_release(self):
        for changes in ({"CAVI_TEST_ISOLATION_CONFIRMED": "false"}, {"CAVI_TEST_RELEASE_ID": "latest"}, {"CAVI_TEST_RELEASE_ID": "main"}, {"CAVI_TEST_RELEASE_ID": ""}, {"CAVI_TEST_RELEASE_ID": "release\n"}):
            with self.subTest(changes=changes), self.assertRaises(ImproperlyConfigured):
                staging_config({**self.env, **changes})

    def test_loaded_settings_isolate_database_tokens_storage_and_outgoing_email(self):
        with patch.dict(os.environ, self.env):
            config = runpy.run_module("config.staging_settings")
        database = config["DATABASES"]["default"]
        self.assertEqual((database["HOST"], database["NAME"], database["USER"]), ("test-db", "cavi_test", "cavi_test"))
        self.assertEqual(database["PASSWORD"], self.env["CAVI_TEST_DB_PASSWORD"])
        self.assertFalse(config["DEBUG"])
        self.assertEqual(config["ALLOWED_HOSTS"], ["staging.cavi.vn"])
        self.assertEqual(config["MEDIA_ROOT"].name, "staging-media")
        self.assertEqual(config["ROOT_URLCONF"], "config.staging_urls")
        self.assertEqual(config["SIMPLE_JWT"]["SIGNING_KEY"], self.env["CAVI_TEST_SECRET_KEY"])
        self.assertEqual(config["SIMPLE_JWT"]["AUDIENCE"], "cavi-test")
        self.assertEqual(config["SIMPLE_JWT"]["ISSUER"], self.env["CAVI_TEST_ORIGIN"])
        self.assertEqual(config["EMAIL_BACKEND"], "django.core.mail.backends.locmem.EmailBackend")
        self.assertFalse(config["CORS_ALLOW_ALL_ORIGINS"])
        self.assertEqual(set(config["CORS_ALLOWED_ORIGINS"]), {self.env["CAVI_TEST_ORIGIN"], "capacitor://localhost", "https://localhost"})
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertIsNone(config["SESSION_COOKIE_DOMAIN"])
        self.assertIn("companyhub", config["INSTALLED_APPS"])
        self.assertIn("notifications", config["INSTALLED_APPS"])
        self.assertTrue(config["CAVI_NOTIFICATIONS_ENABLED"])
        self.assertTrue(config["COMPANY_HUB_ENABLED"])
        self.assertEqual(config["COMPANY_HUB_OWNER_USERNAME"], "cavi-test-owner")

    def test_online_modules_remain_absent_from_production_settings(self):
        production = runpy.run_module("config.settings")
        self.assertNotIn("companyhub", production["INSTALLED_APPS"])
        self.assertNotIn("notifications", production["INSTALLED_APPS"])
        self.assertFalse(production.get("COMPANY_HUB_ENABLED", False))
        self.assertFalse(production.get("CAVI_NOTIFICATIONS_ENABLED", False))

    @override_settings(CAVI_ENVIRONMENT="preview", CAVI_RELEASE_ID="test-001", CAVI_PUBLIC_ORIGIN="https://staging.cavi.vn")
    def test_environment_is_read_only_public_metadata_no_secrets(self):
        request = RequestFactory().get("/api/environment/")
        response = environment(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"environment": "preview"', response.content)
        self.assertNotIn(b"password", response.content)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(environment(RequestFactory().post("/api/environment/")).status_code, 405)

    def test_health_hides_database_error_details(self):
        with patch("config.staging_views.connection") as database:
            database.cursor.side_effect = RuntimeError("sensitive connection details")
            response = health(RequestFactory().get("/healthz/"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"sensitive", response.content)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_test_metadata_and_health_not_added_to_production(self):
        self.assertEqual(self.client.get("/api/environment/").status_code, 404)
        self.assertEqual(self.client.get("/healthz/").status_code, 404)
