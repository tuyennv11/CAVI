from django.core.management.base import BaseCommand

from companies.models import Company

# (code, tên hiển thị, loại hình) — thêm 1 công ty thương mại mới sau này thì thêm dòng ở đây (hoặc
# tạo thẳng qua trang admin — công ty không bắt buộc phải seed qua đây, chỉ tiện lúc khởi tạo đầu).
SEED_COMPANIES = [
    ("CAVI", "CAVI", Company.BusinessType.TRANSPORT),
    ("LIVI", "LIVI", Company.BusinessType.TRADING),
    ("AVI", "AVI", Company.BusinessType.TRADING),
]


class Command(BaseCommand):
    help = "Tạo sẵn các công ty: CAVI (Vận chuyển), LIVI, AVI (Thương mại)"

    def handle(self, *args, **options):
        for code, name, business_type in SEED_COMPANIES:
            _, created = Company.objects.get_or_create(
                code=code, defaults={"name": name, "business_type": business_type}
            )
            status = "đã tạo" if created else "đã có sẵn"
            self.stdout.write(f"Công ty '{code}': {status}")
