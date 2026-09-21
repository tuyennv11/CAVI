# Bước 2/3 đổi cấu trúc PriceRequest (đổi tên từ PriceInquiry tuần trước) sang mô hình nhiều sản
# phẩm/yêu cầu — chuyển item_name/quantity/unit/image hiện có (nếu có) thành 1 PriceRequestItem đầu
# tiên cho mỗi Yêu cầu giá, và remap status cũ (open/quoted/cancelled) sang bộ trạng thái quy trình
# mới. Field cũ được xoá thật ở bước 3 (0051), sau khi dữ liệu đã chuyển an toàn sang đây.

from django.db import migrations

STATUS_MAP = {
    "open": "cho_cung_ung",
    "quoted": "cho_duyet",
    "cancelled": "huy",
}
REVERSE_STATUS_MAP = {v: k for k, v in STATUS_MAP.items()}


def forwards(apps, schema_editor):
    PriceRequest = apps.get_model("crm", "PriceRequest")
    PriceRequestItem = apps.get_model("crm", "PriceRequestItem")

    for pr in PriceRequest.objects.all():
        if pr.item_name or pr.quantity or pr.unit or pr.image:
            PriceRequestItem.objects.create(
                price_request=pr,
                item_name=pr.item_name,
                quantity=pr.quantity,
                unit=pr.unit,
                image=pr.image,
            )
        old_status = pr.status
        if old_status in STATUS_MAP:
            pr.status = STATUS_MAP[old_status]
            pr.save(update_fields=["status"])


def backwards(apps, schema_editor):
    PriceRequest = apps.get_model("crm", "PriceRequest")
    PriceRequestItem = apps.get_model("crm", "PriceRequestItem")

    for pr in PriceRequest.objects.all():
        first_item = pr.items.order_by("id").first()
        if first_item is not None:
            pr.item_name = first_item.item_name
            pr.quantity = first_item.quantity
            pr.unit = first_item.unit
            pr.image = first_item.image
        old_status = pr.status
        if old_status in REVERSE_STATUS_MAP:
            pr.status = REVERSE_STATUS_MAP[old_status]
        pr.save()
    PriceRequestItem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0049_alter_pricerequest_options_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
