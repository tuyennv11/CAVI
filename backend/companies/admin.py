from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "business_type", "legal_name", "tax_code", "hotline", "address",
        "is_active", "created_at",
    )
    list_filter = ("business_type", "is_active")
    search_fields = ("name", "code", "legal_name", "tax_code")
