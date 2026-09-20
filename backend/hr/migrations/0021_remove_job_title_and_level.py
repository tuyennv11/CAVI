# Chỉnh tay: Chức vụ đổi từ job_title (chữ) + level (danh sách chọn) sang danh mục Chức vụ riêng.
# Bước 3/3 — dữ liệu đã chuyển hết sang `position` ở 0020, giờ xoá hẳn 2 field cũ.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0020_seed_positions_and_migrate_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="job_title",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="level",
        ),
    ]
