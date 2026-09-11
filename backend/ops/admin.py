from django.contrib import admin

from config.admin_utils import linked_fk

from .models import Shipment, ShipmentBatch


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner_link",
        "description",
        "tracking_code",
        "route",
        "kd_status",
        "cu_status",
        "vh_status",
        "kt_status",
        "amount",
        "currency",
        "assigned_operator",
        "batch",
        "created_by",
        "created_at",
    )
    list_filter = ("kd_status", "cu_status", "vh_status", "kt_status")
    search_fields = ("tracking_code", "description")

    @admin.display(description="Đối tác")
    def partner_link(self, obj):
        return linked_fk(obj.partner)


@admin.register(ShipmentBatch)
class ShipmentBatchAdmin(admin.ModelAdmin):
    list_display = ("route", "status", "operator", "created_at")
    list_filter = ("status",)
