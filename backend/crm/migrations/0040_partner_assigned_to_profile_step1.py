# Bước 1/3 đổi "Nhân viên phụ trách" (assigned_to) của Đối tác từ liên kết Tài khoản đăng nhập (User)
# sang Hồ sơ nhân sự (hr.Profile) — thêm field tạm song song, chưa đụng field cũ.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0039_partner_code_unique'),
        ('hr', '0027_remove_profile_rooms_delete_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='assigned_to_profile',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='partners_new', to='hr.profile', verbose_name='Nhân sự phụ trách',
            ),
        ),
    ]
