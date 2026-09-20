import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

# Cloudflare/nginx đứng trước Django và lo phần HTTPS — kết nối thật tới gunicorn là HTTP thường,
# nên phải khai báo header này để request.is_secure() (và build_absolute_uri()) trả về đúng https,
# nếu không các URL tuyệt đối tự sinh (vd ảnh hỏi giá) sẽ ra http:// và bị trình duyệt chặn mixed-content.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "import_export",
    "accounts",
    "companies",
    "geo",
    "crm",
    "approvals",
    "hr",
    "ops",
    "inventory",
    "finance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # templates/admin/base_site.html ghi đè CSS trang admin (xem file đó) — phải khai DIRS ở
        # đây vì app_directories chỉ tự tìm bên trong từng app, không tìm ở thư mục gốc project.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---
# Set POSTGRES_* env vars (see docker-compose.yml) for real usage.
# Falls back to SQLite so the project also runs with zero setup for local dev/testing.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF / JWT ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
}

# --- CORS (React dev server + production frontend origin) ---
CORS_ALLOW_HEADERS = (*default_headers, "x-company-id")
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,https://app.vantaiduongbo.net"
    ).split(",")
    if o.strip()
]

# --- App-level role group names (created by: manage.py seed_groups) ---
GROUP_MANAGER = "Quản lý"
GROUP_SALES = "Nhân viên kinh doanh"
GROUP_HR = "Nhân sự"
GROUP_ACCOUNTING = "Kế toán"
GROUP_SUPPLY = "Cung ứng"

# --- Thông tin công ty in trên PDF báo giá — chưa có hotline chính thức, để trống, điền qua env sau ---
COMPANY_HOTLINE = os.environ.get("COMPANY_HOTLINE", "")

# --- Hạn mức công nợ theo hạng đối tác (đơn vị: VNĐ) — sửa số ở đây nếu công ty đổi chính sách ---
TIER_CREDIT_LIMITS = {
    "standard": 50_000_000,
    "vip": 200_000_000,
    "super_vip": 500_000_000,
}

# --- Điều kiện tự động lên hạng: phải đạt CẢ HAI (đủ thời gian gắn bó VÀ đủ doanh thu tích luỹ) ---
TIER_TENURE_MONTHS = {
    "vip": 6,
    "super_vip": 12,
}
TIER_REVENUE_THRESHOLDS = {
    "vip": 500_000_000,
    "super_vip": 2_000_000_000,
}

# --- Xuất/nhập Excel ở trang admin (django-import-export) — xem config/admin_import_export.py ---
from import_export.formats.base_formats import XLSX  # noqa: E402


class SafeXLSX(XLSX):
    """Thay cho XLSX gốc — TablibFormat._escape_formulae() (chạy khi
    IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT=True) làm str(cell) cho MỌI ô vô điều kiện, biến None/
    False/Decimal/datetime thành chữ ("None", "False", "10.00"...) rồi lúc Nhập lại không đọc được
    (phát hiện qua test round-trip thực tế: NOT NULL/decimal.ConversionSyntax ở mọi ô trống hoặc số).
    Ghi đè lại: chỉ xử lý ô nào ĐÃ LÀ chuỗi và bắt đầu bằng "=", giữ nguyên kiểu dữ liệu gốc các ô khác
    — vẫn chặn được công thức độc hại trong ô văn bản, không phá hỏng số/ngày/boolean/ô trống.
    """

    def _escape_formulae(self, dataset):
        for _ in dataset:
            row = dataset.lpop()
            row = [
                cell.replace("=", "", 1) if isinstance(cell, str) and cell.startswith("=") else cell
                for cell in row
            ]
            dataset.append(row)


IMPORT_EXPORT_FORMATS = [SafeXLSX]              # chỉ Excel, không hiện thêm lựa chọn CSV/JSON
IMPORT_EXPORT_USE_TRANSACTIONS = True           # lỗi 1 dòng thì rollback cả file, không nhập dở dang
IMPORT_EXPORT_SKIP_ADMIN_LOG = False            # vẫn ghi "Hoạt động gần đây" khi nhập qua Excel
IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT = True  # chặn công thức lạ kiểu =CMD(...) lẫn trong dữ liệu
