# Gán mã "DT0000000001" tăng dần theo đúng thứ tự id cho những Đối tác đã có sẵn (field "code" vừa
# thêm ở 0037 — dòng cũ được thêm với code rỗng theo quy tắc thêm field CharField không NULL).

from django.db import migrations


def backfill_codes(apps, schema_editor):
    Partner = apps.get_model("crm", "Partner")
    next_number = 1
    for partner in Partner.objects.filter(code="").order_by("id"):
        while Partner.objects.filter(code=f"DT{next_number:010d}").exists():
            next_number += 1
        partner.code = f"DT{next_number:010d}"
        partner.save(update_fields=["code"])
        next_number += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0037_partner_redesign_excel_sheet"),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop),
    ]
