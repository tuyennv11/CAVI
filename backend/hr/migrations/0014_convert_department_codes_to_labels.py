# Chỉnh tay: department vừa bỏ danh sách chọn sẵn (0013), chuyển thành ô nhập tự do — đổi các giá
# trị đang lưu dạng mã cũ (sales, supply...) sang đúng nhãn tiếng Việt đã hiện trước đó, để dữ liệu
# hồ sơ đang có không biến thành mã khó hiểu sau khi bỏ choices.

from django.db import migrations

CODE_TO_LABEL = {
    "sales": "Kinh doanh",
    "supply": "Cung ứng",
    "operations": "Vận hành",
    "accounting": "Kế toán",
    "hr": "Nhân sự",
    "management": "Quản lý",
}


def codes_to_labels(apps, schema_editor):
    Profile = apps.get_model("hr", "Profile")
    for code, label in CODE_TO_LABEL.items():
        Profile.objects.filter(department=code).update(department=label)


def labels_to_codes(apps, schema_editor):
    Profile = apps.get_model("hr", "Profile")
    for code, label in CODE_TO_LABEL.items():
        Profile.objects.filter(department=label).update(department=code)


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0013_room_alter_profile_options_and_more"),
    ]

    operations = [
        migrations.RunPython(codes_to_labels, labels_to_codes),
    ]
