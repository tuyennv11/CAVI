"""Online TEST only; never use local DEBUG preview settings on the Internet."""

from .settings import *  # noqa: F403
from .staging_config import staging_config

_test = staging_config(os.environ)  # noqa: F405
DEBUG = False
SECRET_KEY = _test["secret"]
ALLOWED_HOSTS = [_test["host"]]
ROOT_URLCONF = "config.staging_urls"
CAVI_ENVIRONMENT = "preview"
CAVI_QUOTATION_PDF_ATLAS = True
# Match the TEST UI's routes without enabling these apps in production settings.
# The online owner is the isolated synthetic seed account, never the local HR user.
INSTALLED_APPS = [*INSTALLED_APPS, "companyhub", "notifications"]  # noqa: F405
CAVI_NOTIFICATIONS_ENABLED = True
COMPANY_HUB_ENABLED = True
COMPANY_HUB_OWNER_USERNAME = "cavi-test-owner"
CAVI_RELEASE_ID = _test["release"]
CAVI_PUBLIC_ORIGIN = _test["origin"]
PREVIEW_APP_URL = f"{CAVI_PUBLIC_ORIGIN}/preview-data"

# These fixed identifiers belong to docker-compose.staging.yml, not to prod.
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "cavi_test",
    "USER": "cavi_test",
    "PASSWORD": _test["password"],
    "HOST": "test-db",
    "PORT": "5432",
    "CONN_MAX_AGE": 60,
}}
MEDIA_ROOT = BASE_DIR / "staging-media"  # noqa: F405
CORS_ALLOWED_ORIGINS = [CAVI_PUBLIC_ORIGIN, "capacitor://localhost", "https://localhost"]
CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = [CAVI_PUBLIC_ORIGIN]
SESSION_COOKIE_NAME = "cavi_test_session"
CSRF_COOKIE_NAME = "cavi_test_csrf"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = "DENY"

# The backend is only reachable on an isolated Docker network through nginx.
# nginx overwrites the forwarded proto; it never trusts the client's header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_HOST = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "cavi-test"}}
SIMPLE_JWT = {
    "SIGNING_KEY": SECRET_KEY,
    "ISSUER": CAVI_PUBLIC_ORIGIN,
    "AUDIENCE": "cavi-test",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # noqa: F405
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),  # noqa: F405
}
