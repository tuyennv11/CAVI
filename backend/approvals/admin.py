from django.contrib import admin

from config.admin_utils import truncated

from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title", "request_type", "category", "note_short", "related_url", "amount", "currency",
        "status", "requested_by", "reviewed_by", "reviewed_at", "created_at",
    )
    list_filter = ("request_type", "status")

    @admin.display(description="Ghi chú")
    def note_short(self, obj):
        return truncated(obj.note)
