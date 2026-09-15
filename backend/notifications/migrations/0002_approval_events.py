from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [migrations.AlterField(model_name="notification", name="kind", field=models.CharField(max_length=30, choices=[
        ("task_assigned", "Được giao công việc"), ("task_updated", "Công việc thay đổi"),
        ("notice_published", "Thông báo nội bộ mới"), ("notice_updated", "Thông báo nội bộ thay đổi"),
        ("approval_submitted", "Yêu cầu mới cần duyệt"), ("approval_updated", "Nội dung trình duyệt thay đổi"),
        ("approval_approved", "Yêu cầu được duyệt"), ("approval_rejected", "Yêu cầu bị từ chối"),
        ("approval_paid", "Yêu cầu được đánh dấu đã chi"),
    ]))]
