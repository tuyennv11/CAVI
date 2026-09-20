# Chỉnh tay: field "code" vừa thêm ở 0025 — bản ghi đã có sẵn (nếu có) được thêm với code rỗng (quy
# tắc thêm field CharField không NULL của Django), giờ gán mã "KC00001" tăng dần theo đúng thứ tự id
# cho những bản ghi đó.

from django.db import migrations


def backfill_codes(apps, schema_editor):
    EmergencyContact = apps.get_model("hr", "EmergencyContact")
    next_number = 1
    for contact in EmergencyContact.objects.filter(code="").order_by("id"):
        while EmergencyContact.objects.filter(code=f"KC{next_number:05d}").exists():
            next_number += 1
        contact.code = f"KC{next_number:05d}"
        contact.save(update_fields=["code"])
        next_number += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0025_emergency_contact_code"),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop),
    ]
