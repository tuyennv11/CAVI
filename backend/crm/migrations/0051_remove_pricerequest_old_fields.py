# Bước 3/3 — xoá field cũ khỏi PriceRequest (đã copy dữ liệu sang PriceRequestItem/PriceCalculation
# ở 0050 và bằng thiết kế Giai đoạn 2 tương ứng). Không lo mất dữ liệu — dữ liệu tuần trước rất ít.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0050_migrate_pricerequest_item_and_status_data'),
    ]

    operations = [
        migrations.RemoveField(model_name='pricerequest', name='ceiling_pct'),
        migrations.RemoveField(model_name='pricerequest', name='ceiling_price'),
        migrations.RemoveField(model_name='pricerequest', name='cost_price'),
        migrations.RemoveField(model_name='pricerequest', name='floor_pct'),
        migrations.RemoveField(model_name='pricerequest', name='floor_price'),
        migrations.RemoveField(model_name='pricerequest', name='image'),
        migrations.RemoveField(model_name='pricerequest', name='item_name'),
        migrations.RemoveField(model_name='pricerequest', name='quantity'),
        migrations.RemoveField(model_name='pricerequest', name='quoted_at'),
        migrations.RemoveField(model_name='pricerequest', name='quoted_by'),
        migrations.RemoveField(model_name='pricerequest', name='unit'),
    ]
