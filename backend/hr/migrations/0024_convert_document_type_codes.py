# Chỉnh tay: "Loại giấy tờ" đổi từ 6 lựa chọn cũ sang 7 lựa chọn mới theo đúng danh mục anh gửi —
# chuyển giá trị đã lưu sang mã mới tương ứng gần nhất.

from django.db import migrations

OLD_TO_NEW = {
    "id_card": "personal",
    "work_contract": "contract",
    "contract_appendix": "contract",
    "degree": "degree_certificate",
    "certificate": "degree_certificate",
    "other": "other",
}

NEW_TO_OLD = {
    "personal": "id_card",
    "contract": "work_contract",
    "degree_certificate": "degree",
    "other": "other",
}


def forwards(apps, schema_editor):
    EmployeeDocument = apps.get_model("hr", "EmployeeDocument")
    for old_code, new_code in OLD_TO_NEW.items():
        EmployeeDocument.objects.filter(doc_type=old_code).update(doc_type=new_code)


def backwards(apps, schema_editor):
    EmployeeDocument = apps.get_model("hr", "EmployeeDocument")
    for new_code, old_code in NEW_TO_OLD.items():
        EmployeeDocument.objects.filter(doc_type=new_code).update(doc_type=old_code)


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0023_update_document_types"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
