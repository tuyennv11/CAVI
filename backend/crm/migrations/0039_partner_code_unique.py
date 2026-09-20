# Mọi Đối tác đã có mã duy nhất sau bước backfill ở 0038 — giờ mới bật ràng buộc unique=True.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0038_backfill_partner_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="code",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True, verbose_name="Id đối tác"),
        ),
    ]
