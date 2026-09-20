# Chỉnh tay: Chức vụ đổi từ job_title (chữ) + level (danh sách chọn) sang danh mục Chức vụ riêng.
# Bước 2/3 — nạp đúng 30 Chức vụ theo danh mục anh lập (giữ đúng Id chức vụ CV001-CV030 dù thứ tự
# hiển thị trong ảnh không tăng dần tuyệt đối, vd Thủ quỹ CV018/CV017/CV016), rồi chuyển job_title cũ
# của từng Hồ sơ nhân sự sang đúng Chức vụ khớp tên (so khớp không phân biệt hoa/thường vì dữ liệu cũ
# viết hoa/thường không đồng nhất, vd "Tổng giám đốc" cũ vs "Tổng Giám đốc" trong danh mục mới) —
# đồng thời tự điền luôn Bộ Phận theo đúng Chức vụ đó. job_title không khớp tên nào thì bỏ trống
# Chức vụ (không tự đoán gán bừa); Bộ Phận của hồ sơ đó giữ nguyên giá trị đã có từ migration 0017.

from django.db import migrations

# (id chức vụ, tên, id bộ phận, cấp bậc) — đúng theo danh mục anh gửi.
POSITIONS = [
    ("CV001", "Nhân viên kinh doanh", "BP001", 3),
    ("CV002", "Trưởng phòng kinh doanh", "BP001", 2),
    ("CV003", "Giám đốc kinh doanh", "BP001", 1),
    ("CV004", "Nhân viên cung ứng", "BP002", 3),
    ("CV005", "Trưởng phòng cung ứng", "BP002", 2),
    ("CV006", "Giám đốc cung ứng", "BP002", 1),
    ("CV007", "Nhân viên kho Việt Nam", "BP003", 3),
    ("CV008", "Phó kho Việt Nam", "BP003", 2),
    ("CV009", "Trưởng kho Việt Nam", "BP003", 1),
    ("CV010", "Nhân viên kho Campuchia", "BP004", 3),
    ("CV011", "Phó kho Campuchia", "BP004", 2),
    ("CV012", "Trưởng kho Campuchia", "BP004", 1),
    ("CV013", "Nhân viên R&D", "BP005", 3),
    ("CV014", "Trưởng phòng R&D", "BP005", 2),
    ("CV015", "Giám đốc R&D", "BP005", 1),
    ("CV018", "Thủ quỹ viên", "BP006", 3),
    ("CV017", "Thủ quỹ phó", "BP006", 2),
    ("CV016", "Thủ quỹ trưởng", "BP006", 1),
    ("CV021", "Kế toán viên", "BP007", 3),
    ("CV020", "Kế toán phó", "BP007", 2),
    ("CV019", "Kế toán trưởng", "BP007", 1),
    ("CV024", "Nhân viên pháp chế", "BP008", 3),
    ("CV023", "Trưởng phòng pháp chế", "BP008", 2),
    ("CV022", "Giám đốc pháp chế", "BP008", 1),
    ("CV027", "Nhân viên HCNS", "BP009", 3),
    ("CV026", "Trưởng phòng HCNS", "BP009", 2),
    ("CV025", "Giám đốc HCNS", "BP009", 1),
    ("CV028", "Trợ lý Tổng Giám đốc", "BP010", 1),
    ("CV029", "Tổng Giám đốc", "BP010", 0),
    ("CV030", "Cổ đông", "BP011", 0),
]


def seed_and_migrate(apps, schema_editor):
    Department = apps.get_model("hr", "Department")
    Position = apps.get_model("hr", "Position")
    Profile = apps.get_model("hr", "Profile")

    dept_by_code = {d.code: d for d in Department.objects.all()}
    by_name_lower = {}
    for code, name, bp_code, level in POSITIONS:
        dept = dept_by_code.get(bp_code)
        if dept is None:
            continue  # môi trường chưa chạy 0017 seed đủ 11 bộ phận (không nên xảy ra) — bỏ qua an toàn
        pos, _ = Position.objects.get_or_create(
            code=code, defaults={"name": name, "department_id": dept.id, "level": level}
        )
        by_name_lower[name.lower()] = pos

    for profile in Profile.objects.exclude(job_title="").exclude(job_title__isnull=True):
        pos = by_name_lower.get(profile.job_title.strip().lower())
        if pos is None:
            continue  # tên chức vụ cũ không khớp danh mục mới — để trống, không đoán gán bừa
        profile.position_id = pos.id
        profile.department_id = pos.department_id
        profile.save(update_fields=["position", "department"])


def unmigrate(apps, schema_editor):
    Profile = apps.get_model("hr", "Profile")
    Profile.objects.update(position=None)


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0019_position_and_position_fk"),
    ]

    operations = [
        migrations.RunPython(seed_and_migrate, unmigrate),
    ]
