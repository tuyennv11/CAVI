# Chỉnh tay: đổi "Phòng ban" từ ô nhập tự do sang danh mục Bộ phận riêng.
# Bước 3/3 — dữ liệu đã chuyển hết sang `department_new` ở 0017, giờ xoá hẳn field `department`
# (chữ) cũ rồi đổi tên `department_new` thành `department` — khớp đúng tên field trong models.py.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0017_seed_departments_and_migrate_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="department",
        ),
        migrations.RenameField(
            model_name="profile",
            old_name="department_new",
            new_name="department",
        ),
    ]
