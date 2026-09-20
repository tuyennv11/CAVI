# Gán mã "HG000001" tăng dần theo đúng thứ tự id cho những Hỏi giá đã có sẵn (field "code" vừa thêm
# ở 0045 — dòng cũ được thêm với code rỗng theo quy tắc thêm field CharField không NULL).

from django.db import migrations


def backfill_codes(apps, schema_editor):
    PriceInquiry = apps.get_model("crm", "PriceInquiry")
    next_number = 1
    for inquiry in PriceInquiry.objects.filter(code="").order_by("id"):
        while PriceInquiry.objects.filter(code=f"HG{next_number:06d}").exists():
            next_number += 1
        inquiry.code = f"HG{next_number:06d}"
        inquiry.save(update_fields=["code"])
        next_number += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0045_price_inquiry_item_and_delivery_address"),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop),
    ]
