# Chỉnh tay: đổi "Phòng ban" từ ô nhập tự do sang danh mục Bộ phận riêng (mỗi người 1 bộ phận).
# Bước 1/3 — chỉ thêm model Department + field mới `department_new` (FK, để trống), CHƯA đụng tới
# field `department` (chữ) cũ — giữ nguyên dữ liệu hiện có để bước 2 (0017) đọc và chuyển sang.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0015_renumber_employee_code_to_ns"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(blank=True, editable=False, max_length=20, unique=True, verbose_name="Id bộ phận")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Tên")),
                ("system_code", models.CharField(blank=True, max_length=100, verbose_name="Mã hệ thống")),
            ],
            options={
                "verbose_name": "Bộ phận",
                "verbose_name_plural": "Bộ phận",
                "ordering": ["code"],
            },
        ),
        migrations.AddField(
            model_name="profile",
            name="department_new",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff", to="hr.department", verbose_name="Bộ Phận",
            ),
        ),
    ]
