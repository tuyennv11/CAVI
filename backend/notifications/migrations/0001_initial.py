import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("companies", "0002_alter_company_options")]
    operations = [
        migrations.CreateModel(name="Notification", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ("event_key", models.CharField(max_length=64)),
            ("kind", models.CharField(choices=[("task_assigned", "Được giao công việc"), ("task_updated", "Công việc thay đổi"), ("notice_published", "Thông báo nội bộ mới"), ("notice_updated", "Thông báo nội bộ thay đổi")], max_length=30)),
            ("object_id", models.PositiveBigIntegerField()),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("read_at", models.DateTimeField(blank=True, null=True)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="companies.company")),
            ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-id"],
                    "indexes": [models.Index(fields=["recipient", "company", "read_at", "id"], name="notification_inbox_idx")],
                    "constraints": [models.UniqueConstraint(fields=("recipient", "company", "event_key"), name="notification_once_per_user")]}),
        migrations.CreateModel(name="PushOutbox", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("state", models.CharField(default="not_configured", editable=False, max_length=30)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("notification", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="push_intent", to="notifications.notification")),
        ]),
    ]
