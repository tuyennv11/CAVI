import json
from pathlib import Path

from django.core.management.base import BaseCommand

from geo.models import Country, District, Province, Ward

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "vn_divisions.json"


class Command(BaseCommand):
    help = "Nhập dữ liệu Tỉnh/Thành - Quận/Huyện - Phường/Xã của Việt Nam (nguồn provinces.open-api.vn)."

    def handle(self, *args, **options):
        # Idempotent — bỏ qua nếu đã nhập rồi, tránh chạy lại tốn thời gian mỗi lần deploy
        # (lệnh này được gọi ở mỗi lần khởi động container, giống seed_groups).
        vietnam, _ = Country.objects.get_or_create(code="VN", defaults={"name": "Việt Nam"})
        Country.objects.get_or_create(code="KH", defaults={"name": "Campuchia"})
        Country.objects.get_or_create(code="LA", defaults={"name": "Lào"})

        if Province.objects.filter(country=vietnam).exists():
            self.stdout.write("Dữ liệu hành chính Việt Nam: đã có sẵn")
            return

        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        province_count = district_count = ward_count = 0
        for p in data:
            province = Province.objects.create(
                country=vietnam, name=p["name"], code=str(p["code"]), division_type=p.get("division_type", "")
            )
            province_count += 1
            districts = [
                District(
                    province=province, name=d["name"], code=str(d["code"]), division_type=d.get("division_type", "")
                )
                for d in p["districts"]
            ]
            District.objects.bulk_create(districts)
            district_count += len(districts)

            district_by_code = {d.code: d for d in province.districts.all()}
            wards = []
            for d in p["districts"]:
                district = district_by_code[str(d["code"])]
                for w in d["wards"]:
                    wards.append(
                        Ward(
                            district=district, name=w["name"], code=str(w["code"]),
                            division_type=w.get("division_type", "")
                        )
                    )
            Ward.objects.bulk_create(wards)
            ward_count += len(wards)

        self.stdout.write(
            f"Đã nhập {province_count} tỉnh/thành, {district_count} quận/huyện, {ward_count} phường/xã"
        )
