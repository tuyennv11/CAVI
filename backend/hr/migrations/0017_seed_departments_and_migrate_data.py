# Chỉnh tay: đổi "Phòng ban" từ ô nhập tự do sang danh mục Bộ phận riêng.
# Bước 2/3 — nạp đúng 11 Bộ phận theo danh mục anh lập (id bộ phận tự sinh theo đúng thứ tự chèn,
# xem Department.save()), rồi chuyển dữ liệu "department" (chữ) cũ của từng Hồ sơ nhân sự sang đúng
# Bộ phận mới khớp tên; hồ sơ nào có tên bộ phận cũ KHÔNG khớp Bộ phận nào trong danh mục 11 mục thì
# tự tạo thêm 1 Bộ phận mới đúng tên đó (không bỏ mất dữ liệu, không tự đoán gán bừa sang bộ phận
# khác).

from django.db import migrations

# Đúng thứ tự trong danh mục anh gửi — id bộ phận (BP001, BP002...) tự sinh khớp theo đúng thứ tự
# chèn này (xem Department.save()).
DEPARTMENTS = [
    ("Bộ phận kinh doanh", "Bo_phan_kinh_doanh"),
    ("Bộ phận cung ứng", "Bo_phan_cung_ung"),
    ("Bộ phận kho Việt Nam", "Bo_phan_kho_viet_nam"),
    ("Bộ phận kho Campuchia", "Bo_phan_kho_campuchia"),
    ("Bộ phận R&D", "Bo_phan_r_d"),
    ("Bộ phận thủ quỹ", "Bo_phan_thu_quy"),
    ("Bộ phận tài chính - kế toán", "Bo_phan_tai_chinh_ke_toan"),
    ("Bộ phận pháp chế", "Bo_phan_phap_che"),
    ("Bộ phận hành chính nhân sự", "Bo_phan_hanh_chinh_nhan_su"),
    ("Tổng giám đốc", "Bo_phan_tong_giam_doc"),
    ("Cổ đông", "Bo_phan_co_dong"),
]


def seed_and_migrate(apps, schema_editor):
    Department = apps.get_model("hr", "Department")
    Profile = apps.get_model("hr", "Profile")

    # apps.get_model() trả về model "trần" chỉ có field, KHÔNG có method save() tuỳ biến của
    # Department (tự sinh "code") — nên phải tự gán code rõ ràng ở đây, không dựa vào save().
    by_name = {}
    next_code_number = 1
    for name, system_code in DEPARTMENTS:
        dept, _ = Department.objects.get_or_create(
            name=name, defaults={"system_code": system_code, "code": f"BP{next_code_number:03d}"}
        )
        by_name[name] = dept
        next_code_number += 1

    for profile in Profile.objects.exclude(department="").exclude(department__isnull=True):
        old_text = profile.department
        dept = by_name.get(old_text)
        if dept is None:
            # Tên bộ phận cũ không khớp 11 mục trong danh mục — tạo thêm đúng bộ phận đó, không bỏ
            # mất dữ liệu cũ, không tự đoán gán bừa sang bộ phận có sẵn.
            dept, _ = Department.objects.get_or_create(
                name=old_text, defaults={"code": f"BP{next_code_number:03d}"}
            )
            by_name[old_text] = dept
            next_code_number += 1
        profile.department_new_id = dept.id
        profile.save(update_fields=["department_new"])


def unmigrate(apps, schema_editor):
    # Không hoàn tác được — dữ liệu department (chữ) cũ vẫn còn nguyên ở field cũ cho tới migration
    # 0018 (chỉ 0018 mới thật sự xoá nó), nên reverse ở đây chỉ cần xoá field department_new.
    Profile = apps.get_model("hr", "Profile")
    Profile.objects.update(department_new=None)


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0016_department_and_department_fk"),
    ]

    operations = [
        migrations.RunPython(seed_and_migrate, unmigrate),
    ]
