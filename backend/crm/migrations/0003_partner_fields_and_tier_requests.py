import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_company_into_note(apps, schema_editor):
    Partner = apps.get_model("crm", "Partner")
    for p in Partner.objects.exclude(company=""):
        line = f"Công ty: {p.company}"
        p.note = f"{line}\n{p.note}".strip() if p.note else line
        p.save(update_fields=["note"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0002_partner_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="contact_person",
            field=models.CharField(blank=True, max_length=255, verbose_name="Người liên hệ"),
        ),
        migrations.AddField(
            model_name="partner",
            name="note",
            field=models.TextField(blank=True, verbose_name="Mô tả thêm"),
        ),
        migrations.RunPython(copy_company_into_note, noop_reverse),
        migrations.RemoveField(model_name="partner", name="company"),
        migrations.RemoveField(model_name="partner", name="email"),
        migrations.RemoveField(model_name="partner", name="address"),
        migrations.RemoveField(model_name="partner", name="tier"),
        migrations.AddField(
            model_name="partner",
            name="tier_override",
            field=models.CharField(
                blank=True,
                choices=[("standard", "Thường"), ("vip", "VIP"), ("super_vip", "Siêu VIP")],
                max_length=20,
                null=True,
                verbose_name="Hạng đã duyệt vượt bậc",
            ),
        ),
        migrations.CreateModel(
            name="TierUpgradeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "requested_tier",
                    models.CharField(
                        choices=[("standard", "Thường"), ("vip", "VIP"), ("super_vip", "Siêu VIP")],
                        max_length=20,
                        verbose_name="Hạng xin lên",
                    ),
                ),
                ("reason", models.TextField(verbose_name="Lý do")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Đang chờ"), ("approved", "Đã duyệt"), ("rejected", "Từ chối")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "partner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="tier_requests", to="crm.partner"
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
