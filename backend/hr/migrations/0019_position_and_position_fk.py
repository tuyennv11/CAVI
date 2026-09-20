# Chỉnh tay: Chức vụ (job_title chữ + level danh sách chọn) đổi thành danh mục Chức vụ riêng, mỗi
# Chức vụ gắn cứng với 1 Bộ phận + 1 Cấp bậc (số). Chọn Chức vụ sẽ tự điền Bộ Phận (đã editable=False
# từ 0018) — không còn chọn Bộ Phận độc lập với Chức vụ nữa.
# Bước 1/3 — chỉ thêm model Position + field `position` (FK, để trống), CHƯA đụng tới `job_title`/
# `level` cũ — giữ nguyên dữ liệu hiện có để bước 2 (0020) đọc và chuyển sang.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0018_replace_department_char_with_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="Position",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(blank=True, editable=False, max_length=20, unique=True, verbose_name="Id chức vụ")),
                ("name", models.CharField(max_length=100, verbose_name="Tên chức vụ")),
                ("level", models.PositiveSmallIntegerField(verbose_name="Cấp bậc")),
                ("department", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="positions",
                    to="hr.department", verbose_name="Id bộ phận",
                )),
            ],
            options={
                "verbose_name": "Chức vụ",
                "verbose_name_plural": "Chức vụ",
                "ordering": ["department", "level"],
            },
        ),
        migrations.AddField(
            model_name="profile",
            name="position",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff", to="hr.position", verbose_name="Chức vụ",
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="department",
            field=models.ForeignKey(
                blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff", to="hr.department", verbose_name="Bộ Phận",
            ),
        ),
    ]
