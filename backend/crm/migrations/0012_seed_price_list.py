from django.db import migrations

# (category, group_code, group_name, [(name, unit, floor_pct, ceiling_pct), ...])
# Mã mặt hàng gốc trong file gửi vào bị lẫn lộn tiền tố giữa các nhóm (ghi rõ "COI LẠI MÃ") —
# ở đây sinh lại theo quy tắc "<mã nhóm>-<số thứ tự 3 chữ số>" cho đồng bộ và không trùng lặp.
GROUPS = [
    (
        "I", "001", "Vận chuyển hàng ghép quốc tế",
        [
            ("Hàng mẫu - lẻ từ 15-30 kg/ kiện", "kiện", 50, 100),
            ("Hàng thông thường từ 31 - 150kg", "kg, cbm", 40, 80),
            ("Hàng thông thường từ 151-499kg", "kg, cbm", 30, 80),
            ("Hàng thông thường từ 500-999kg", "kg, cbm", 20, 60),
            ("Nhớt", "kg", 20, 60),
            ("Thuốc Tây", "kg", 30, 80),
            ("Linh kiện điện tử", "kg", 20, 50),
            ("Hóa Chất", "kg", 20, 60),
            ("Máy móc", "kg", 20, 60),
            ("Hàng mẫu - lẻ dưới 15kg/ kiện", "kiện", 100, 200),
            ("Hàng mẫu - lẻ đi nhanh dưới 30 kg/ kiện", "kiện", 20, 50),
            ("Hàng thông thường trên 1 tấn", "kg", 15, 50),
            ("Hàng làm đầy xe", "kg", 10, 40),
        ],
    ),
    (
        "I", "002", "Dịch vụ Hải quan & Cơ quan Nhà nước - Chuyên sâu",
        [
            ("Thủ tục hải quan hàng ghép nhập khẩu", "hồ sơ", 10, 300),
            ("Thủ tục hải quan tạm xuất tái nhập có ứng cọc", "hồ sơ", 10, 300),
            ("Thủ tục khác (có tính chất quyết định)", "hồ sơ", 10, 300),
        ],
    ),
    (
        "II", "003", "Dịch vụ Hải quan & Cơ quan Nhà nước - Tiêu chuẩn",
        [
            ("Dịch vụ thanh lý tờ khai hải quan xuất khẩu", "hồ sơ", 5, 50),
            ("Dịch vụ mở tờ khai hải quan xuất khẩu", "hồ sơ", 5, 50),
            ("Dịch vụ thanh lý khai hải quan nhập khẩu", "hồ sơ", 5, 50),
            ("Dịch vụ mở tờ khai hải quan nhập khẩu", "hồ sơ", 5, 50),
            ("Lệ phí hải quan nhập khẩu", "hồ sơ", 5, 50),
            ("Lệ phí hải quan xuất khẩu", "hồ sơ", 5, 50),
            ("Dịch vụ mở hồ sơ hải quan nhập khẩu", "hồ sơ", 5, 50),
            ("Dịch vụ mở hồ sơ hải quan xuất khẩu", "hồ sơ", 5, 50),
        ],
    ),
    (
        "II", "004", "Vận chuyển nguyên xe quốc tế - Xe liên vận",
        [
            ("Mooc lùn", "xe", 15, 50),
            ("Mooc sàn", "xe", 15, 50),
            ("Xe tải thùng", "xe", 15, 50),
            ("Neo xe liên vận", "xe", 0, 0),
        ],
    ),
    (
        "II", "005", "Dịch vụ thu - chi hộ",
        [
            ("Thu Hộ, Ứng Tiền", "lần", 5, 50),
            ("Phí đi giao", "lần", 0, 0),
        ],
    ),
    (
        "II", "006", "Dịch vụ bảo hiểm",
        [
            ("Bảo hiểm hàng hóa", "chuyến", 5, 50),
        ],
    ),
    (
        "III", "007", "Vận chuyển hàng ghép nội địa",
        [
            ("Hàng mẫu - lẻ từ 15-30 kg/ kiện", "kiện", 50, 100),
            ("Hàng thông thường từ 31 - 150kg", "kg, cbm", 40, 80),
            ("Hàng thông thường từ 151-499kg", "kg, cbm", 30, 80),
            ("Hàng thông thường từ 500-999kg", "kg, cbm", 20, 60),
            ("Hàng mẫu - lẻ dưới 15kg/ kiện", "kiện", 100, 200),
            ("Hàng mẫu - lẻ đi nhanh dưới 30 kg/ kiện", "kiện", 20, 50),
            ("Hàng thông thường trên 1 tấn", "kg", 15, 50),
            ("Hàng làm đầy xe", "kg", 10, 40),
        ],
    ),
    (
        "III", "008", "Vận chuyển nguyên xe nội địa",
        [
            ("Mooc lùn", "xe", 15, 50),
            ("Mooc sàn", "xe", 15, 50),
            ("Xe tải thùng", "xe", 15, 50),
            ("Neo xe", "xe", 0, 0),
        ],
    ),
    (
        "III", "009", "Dịch vụ đóng gói",
        [
            ("Quấn PE", "kiện", 15, 50),
            ("Đóng thùng carton", "kiện", 15, 50),
            ("Đóng thùng xốp", "kiện", 15, 50),
            ("Đóng kiện gỗ hở", "kiện", 15, 50),
            ("Đóng kiện gỗ kín", "kiện", 15, 50),
            ("Pallet", "kiện", 15, 50),
            ("Đóng gói hình thức khác", "kiện", 15, 50),
        ],
    ),
    (
        "III", "010", "Dịch vụ nâng hạ",
        [
            ("Bốc xếp tay", "kg", 15, 50),
            ("Xe nâng", "kg", 15, 50),
            ("Xe cẩu", "kg", 15, 50),
            ("Nâng hạ chung (kết hợp)", "kg", 15, 50),
        ],
    ),
    (
        # Dòng cuối trong file gửi vào bị cắt mất % giá trần — tạm để bằng "Dịch vụ nâng hạ"
        # (cùng là dịch vụ nội địa, mức phổ biến nhất trong bảng 15/50), sửa lại trong Admin nếu sai.
        "III", "011", "Dịch vụ lưu kho",
        [
            ("Lưu kho", "m2", 15, 50),
        ],
    ),
]


def seed_price_list(apps, schema_editor):
    PriceListItem = apps.get_model("crm", "PriceListItem")
    for category, group_code, group_name, items in GROUPS:
        for seq, (name, unit, floor_pct, ceiling_pct) in enumerate(items, start=1):
            PriceListItem.objects.update_or_create(
                item_code=f"{group_code}-{seq:03d}",
                defaults={
                    "category": category,
                    "group_code": group_code,
                    "group_name": group_name,
                    "name": name,
                    "unit": unit,
                    "floor_pct": floor_pct,
                    "ceiling_pct": ceiling_pct,
                    "is_active": True,
                },
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0011_pricelistitem_priceinquiryquoteline"),
    ]

    operations = [
        migrations.RunPython(seed_price_list, noop_reverse),
    ]
