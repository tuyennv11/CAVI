from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from config import admin_site  # noqa: F401 — sắp xếp lại trang admin theo luồng nghiệp vụ.
