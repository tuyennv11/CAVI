import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def copy_contactlog_to_activity(apps, schema_editor):
    ContactLog = apps.get_model("crm", "ContactLog")
    Activity = apps.get_model("crm", "Activity")
    outcome_to_result = {
        "pending": "Đang chờ",
        "success": "Thành công",
        "not_closed": "Không chốt",
        "received": "Đã nhận",
    }
    for log in ContactLog.objects.all():
        Activity.objects.create(
            customer_id=log.customer_id,
            activity_type="note",
            title=(log.note or "Ghi chú chăm sóc")[:60],
            activity_at=log.created_at,
            performed_by_id=log.created_by_id,
            assigned_to_id=log.created_by_id,
            contact_person=log.contact_person,
            content=log.note,
            result=outcome_to_result.get(log.outcome, ""),
            status="done",
            created_by_id=log.created_by_id,
            created_at=log.created_at,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0004_notice"),
    ]

    operations = [
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "activity_type",
                    models.CharField(
                        choices=[
                            ("call", "Cuộc gọi"),
                            ("email", "Email"),
                            ("message", "Tin nhắn"),
                            ("meeting", "Gặp mặt"),
                            ("note", "Ghi chú"),
                            ("task", "Công việc cần làm"),
                            ("follow_up", "Follow-up"),
                            ("appointment", "Lịch hẹn / cuộc họp"),
                            ("opportunity", "Cơ hội kinh doanh"),
                            ("quote", "Báo giá"),
                            ("order", "Đơn hàng"),
                            ("contract", "Hợp đồng"),
                            ("payment", "Thanh toán"),
                            ("support_request", "Yêu cầu hỗ trợ"),
                            ("complaint", "Khiếu nại"),
                            ("issue_handling", "Xử lý sự cố"),
                            ("post_sale_care", "Chăm sóc sau bán hàng"),
                        ],
                        max_length=20,
                        verbose_name="Loại hoạt động",
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Tiêu đề")),
                ("activity_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Ngày giờ")),
                ("contact_person", models.CharField(blank=True, max_length=255, verbose_name="Người liên hệ")),
                ("content", models.TextField(blank=True, verbose_name="Nội dung")),
                ("result", models.TextField(blank=True, verbose_name="Kết quả")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("not_processed", "Chưa xử lý"),
                            ("in_progress", "Đang xử lý"),
                            ("done", "Hoàn thành"),
                            ("cancelled", "Huỷ"),
                        ],
                        default="not_processed",
                        max_length=20,
                    ),
                ),
                ("follow_up_date", models.DateField(blank=True, null=True, verbose_name="Ngày cần follow-up")),
                ("note", models.TextField(blank=True, verbose_name="Ghi chú")),
                (
                    "attachment",
                    models.FileField(blank=True, null=True, upload_to="activities/%Y/%m/", verbose_name="File đính kèm"),
                ),
                (
                    "related_reference",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Tham chiếu khác (báo giá/hợp đồng/cơ hội/phiếu hỗ trợ...)",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Người phụ trách",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="crm.partner"
                    ),
                ),
                (
                    "performed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Người thực hiện",
                    ),
                ),
                (
                    "related_order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activities",
                        to="crm.order",
                        verbose_name="Đơn hàng liên quan",
                    ),
                ),
            ],
            options={
                "ordering": ["-activity_at"],
            },
        ),
        migrations.RunPython(copy_contactlog_to_activity, noop_reverse),
        migrations.DeleteModel(name="ContactLog"),
    ]
