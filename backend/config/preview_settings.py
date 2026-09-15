"""Local design session: isolated copy of the data, never a production setting."""

import json
import sys
from pathlib import Path

# A copied Windows venv may provide pure Python Django, but must not shadow
# native Mac packages (notably Pillow's compiled image decoder for PDF export).
_copied_packages = str(Path(__file__).resolve().parents[1] / "venv" / "Lib" / "site-packages")
if sys.platform != "win32" and _copied_packages in sys.path:
    sys.path.remove(_copied_packages)
    sys.path.append(_copied_packages)

from .settings import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
SECRET_KEY = "cavi-local-preview-only-not-for-deployment"
# Real imported HR data requires a private, randomly generated local signing key.
_preview_key = BASE_DIR / ".preview" / "secret-key"  # noqa: F405
if _preview_key.is_file():
    SECRET_KEY = _preview_key.read_text(encoding="utf-8").strip()
    SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405
INSTALLED_APPS = [*INSTALLED_APPS, "companyhub", "notifications"]  # noqa: F405
CAVI_NOTIFICATIONS_ENABLED = True
CAVI_QUOTATION_PDF_ATLAS = True
_preview_access = BASE_DIR / ".preview" / "access.json"  # noqa: F405
COMPANY_HUB_OWNER_USERNAME = json.loads(_preview_access.read_text(encoding="utf-8"))["username"] if _preview_access.is_file() else None
COMPANY_HUB_ENABLED = _preview_key.is_file() and bool(COMPANY_HUB_OWNER_USERNAME)
ROOT_URLCONF = "config.preview_urls"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / ".preview" / "db.sqlite3",  # noqa: F405
}}
MEDIA_ROOT = BASE_DIR / ".preview" / "media"  # noqa: F405
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "cavi_preview_session"
CSRF_COOKIE_NAME = "cavi_preview_csrf"
PREVIEW_APP_URL = "http://localhost:5173/preview-data"
