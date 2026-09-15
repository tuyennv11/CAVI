# Chỉnh tay: công ty chuyển sang chỉ vận hành 1 mình LIVI — tắt CAVI/AVI (is_active=False) thay vì
# xoá, giữ nguyên toàn bộ dữ liệu lịch sử (CAVI có 9 đơn hàng/3 đối tác thật). Mọi nơi trong hệ thống
# đã lọc theo is_active sẵn (get_active_company, /api/companies/, MeSerializer...) nên tắt 1 chỗ này
# là đủ để giao diện tự rút về còn đúng 1 công ty.

from django.db import migrations


def deactivate_cavi_avi(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Company.objects.filter(code__in=["CAVI", "AVI"]).update(is_active=False)


def reactivate_cavi_avi(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Company.objects.filter(code__in=["CAVI", "AVI"]).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0002_alter_company_options"),
    ]

    operations = [
        migrations.RunPython(deactivate_cavi_avi, reactivate_cavi_avi),
    ]
