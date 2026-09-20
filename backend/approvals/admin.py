from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import ApprovalRequest


class ApprovalRequestResource(ExcelModelResource):
    class Meta:
        model = ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(ImportExportModelAdmin):
    resource_classes = [ApprovalRequestResource]
    list_display = (
        "title", "request_type", "category", "note", "related_url", "amount", "currency",
        "status", "requested_by", "reviewed_by", "reviewed_at", "created_at",
    )
    list_filter = ("request_type", "status")
