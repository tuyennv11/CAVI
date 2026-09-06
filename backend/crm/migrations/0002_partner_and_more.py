import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(old_name="Customer", new_name="Partner"),
        migrations.AlterField(
            model_name="partner",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Tên"),
        ),
        migrations.AlterField(
            model_name="partner",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="partners",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Nhân viên phụ trách",
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="partner_type",
            field=models.CharField(
                choices=[
                    ("customer", "Khách hàng"),
                    ("supplier", "Nhà cung cấp"),
                    ("both", "Khách hàng - Nhà cung cấp"),
                ],
                default="customer",
                max_length=20,
                verbose_name="Loại đối tác",
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="tier",
            field=models.CharField(
                choices=[("standard", "Thường"), ("vip", "VIP"), ("super_vip", "Siêu VIP")],
                default="standard",
                max_length=20,
                verbose_name="Hạng",
            ),
        ),
        migrations.AddField(
            model_name="contactlog",
            name="contact_person",
            field=models.CharField(blank=True, max_length=255, verbose_name="Người liên hệ"),
        ),
        migrations.AddField(
            model_name="contactlog",
            name="outcome",
            field=models.CharField(
                choices=[
                    ("pending", "Đang chờ"),
                    ("success", "Thành công"),
                    ("not_closed", "Không chốt"),
                    ("received", "Đã nhận"),
                ],
                default="pending",
                max_length=20,
                verbose_name="Kết quả",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="paid",
            field=models.BooleanField(default=False, verbose_name="Đã thanh toán"),
        ),
        migrations.AddField(
            model_name="order",
            name="on_platform",
            field=models.BooleanField(default=False, verbose_name="Qua sàn"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_cost",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Giá vốn"),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Đơn giá bán"),
        ),
    ]
