# Mọi Hỏi giá đã có mã duy nhất sau bước backfill ở 0046 — giờ mới bật ràng buộc unique=True.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0046_backfill_price_inquiry_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="priceinquiry",
            name="code",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True, verbose_name="Id hỏi giá"),
        ),
    ]
