# Chỉnh tay: bỏ AlterField "assigned_to" ra khỏi migration này — đổi thẳng "to=" model của 1 FK đã
# có dữ liệu (User -> hr.Profile) KHÔNG tự chuyển đổi giá trị, số id cũ (User.id) sẽ bị hiểu nhầm
# thành Profile.id sai hoàn toàn. Việc đổi liên kết được tách ra 3 migration riêng theo đúng mẫu đã
# dùng cho Profile.department/Profile.position (xem hr/migrations 0016-0018, 0019-0021): thêm field
# tạm -> RunPython chuyển dữ liệu theo đúng User -> Profile tương ứng -> xoá field cũ + đổi tên field
# tạm (xem 0038_partner_assigned_to_profile_step1.py trở đi).
#
# Cũng bỏ unique=True ra khỏi field "code" ở bước này — bảng đã có sẵn dữ liệu (không phải model mới
# tinh như Department lúc trước), thêm field unique với default rỗng cho MỌI dòng cùng lúc thì các
# dòng cùng "" đụng UNIQUE constraint ngay lập tức. Tách unique=True sang bước riêng SAU khi đã backfill
# xong mã cho từng dòng (xem 0038_backfill_partner_codes.py, 0039_partner_code_unique.py).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0036_partner_companies'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='code',
            field=models.CharField(blank=True, editable=False, max_length=20, verbose_name='Id đối tác'),
        ),
        migrations.AddField(
            model_name='partner',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Người tạo'),
        ),
        migrations.AddField(
            model_name='partner',
            name='status',
            field=models.CharField(choices=[('dang_hoat_dong', 'Đang hoạt động'), ('tam_ngung', 'Tạm ngừng'), ('ngung_hop_tac', 'Ngừng hợp tác')], default='dang_hoat_dong', max_length=20, verbose_name='Trạng thái'),
        ),
        migrations.AddField(
            model_name='partner',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Tên đối tác'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='tier_override',
            field=models.CharField(blank=True, choices=[('standard', 'Thường'), ('vip', 'VIP'), ('super_vip', 'Siêu VIP')], max_length=20, null=True, verbose_name='Xếp hạng'),
        ),
    ]
