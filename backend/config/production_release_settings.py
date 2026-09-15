"""Approved production promotion; never inherit isolated TEST credentials/data."""
from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403

_release = "cavi-stable-20260914-001"
if os.environ.get("CAVI_PRODUCTION_PROMOTION_CONFIRMED") != _release:  # noqa: F405
    raise ImproperlyConfigured("Explicit production release confirmation is required.")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql" or DATABASES["default"]["NAME"] != "crm":  # noqa: F405
    raise ImproperlyConfigured("Production release must use the existing crm PostgreSQL database.")

# SECRET_KEY/JWT, database credentials, media paths and business roles stay as
# configured by the existing production environment; no TEST settings import.
DEBUG = False
ALLOWED_HOSTS = ["app.vantaiduongbo.net"]
CAVI_ENVIRONMENT = "production"
CAVI_RELEASE_ID = _release
CAVI_QUOTATION_PDF_ATLAS = True
INSTALLED_APPS = [*INSTALLED_APPS, "companyhub", "notifications"]  # noqa: F405
CAVI_NOTIFICATIONS_ENABLED = True
COMPANY_HUB_ENABLED = True
# Read-only production inventory verified the sole active owner (id 1).
COMPANY_HUB_OWNER_USERNAME = "tuyen"
ROOT_URLCONF = "config.production_release_urls"
