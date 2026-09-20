from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource
from config.admin_utils import linked_fk

from .models import Shipment, ShipmentBatch


class ShipmentResource(ExcelModelResource):
    class Meta:
        model = Shipment


class ShipmentBatchResource(ExcelModelResource):
    class Meta:
        model = ShipmentBatch


@admin.register(Shipment)
class ShipmentAdmin(ImportExportModelAdmin):
    resource_classes = [ShipmentResource]
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
class ShipmentBatchAdmin(ImportExportModelAdmin):
    resource_classes = [ShipmentBatchResource]
    list_display = ("route", "status", "operator", "created_at")
    list_filter = ("status",)
