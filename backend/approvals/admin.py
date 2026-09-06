from django.contrib import admin

from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "request_type", "amount", "currency", "status", "requested_by", "created_at")
    list_filter = ("request_type", "status")
