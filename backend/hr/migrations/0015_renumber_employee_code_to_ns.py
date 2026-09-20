# Chỉnh tay: đổi định dạng "Id nhân sự" tự sinh từ "NV-00001" sang "NS000001" cho khớp đúng mẫu
# Excel anh gửi — đổi luôn các mã đã có sẵn (giữ nguyên số thứ tự, chỉ đổi cách viết) để không lẫn 2
# kiểu mã trong cùng hệ thống.

import re

from django.db import migrations

OLD_CODE_RE = re.compile(r"^NV-(\d+)$")


def nv_dash_to_ns(apps, schema_editor):
    Profile = apps.get_model("hr", "Profile")
    for profile in Profile.objects.all():
        match = OLD_CODE_RE.match(profile.employee_code)
        if match:
            profile.employee_code = f"NS{int(match.group(1)):06d}"
            profile.save(update_fields=["employee_code"])


def ns_to_nv_dash(apps, schema_editor):
    Profile = apps.get_model("hr", "Profile")
    for profile in Profile.objects.all():
        if profile.employee_code.startswith("NS") and profile.employee_code[2:].isdigit():
            profile.employee_code = f"NV-{int(profile.employee_code[2:]):05d}"
            profile.save(update_fields=["employee_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0014_convert_department_codes_to_labels"),
    ]

    operations = [
        migrations.RunPython(nv_dash_to_ns, ns_to_nv_dash),
    ]
