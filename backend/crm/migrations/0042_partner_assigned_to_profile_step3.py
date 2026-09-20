# Bước 3/3 — xoá field cũ (User), đổi tên field tạm thành "assigned_to" luôn, và đổi related_name
# về đúng "partners" như thiết kế cuối cùng (bước 1 tạm dùng "partners_new" để không đụng độ với field
# cũ đang còn tồn tại lúc đó).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0041_partner_assigned_to_profile_step2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='partner',
            name='assigned_to',
        ),
        migrations.RenameField(
            model_name='partner',
            old_name='assigned_to_profile',
            new_name='assigned_to',
        ),
        migrations.AlterField(
            model_name='partner',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='partners', to='hr.profile', verbose_name='Nhân sự phụ trách',
            ),
        ),
    ]
