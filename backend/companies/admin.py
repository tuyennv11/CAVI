from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import Company


class CompanyResource(ExcelModelResource):
    class Meta:
        model = Company
        exclude = ("logo",)  # FileField — không xuất/nhập file qua Excel, xem admin_import_export.py


@admin.register(Company)
class CompanyAdmin(ImportExportModelAdmin):
    resource_classes = [CompanyResource]
    list_display = (
        "name", "code", "business_type", "legal_name", "tax_code", "hotline", "address",
        "is_active", "created_at",
    )
    list_filter = ("business_type", "is_active")
    search_fields = ("name", "code", "legal_name", "tax_code")
