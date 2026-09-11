from django.contrib import admin

from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title", "request_type", "category", "note", "related_url", "amount", "currency",
        "status", "requested_by", "reviewed_by", "reviewed_at", "created_at",
    )
    list_filter = ("request_type", "status")
