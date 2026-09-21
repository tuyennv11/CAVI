import json
from pathlib import Path

from django.core.management.base import BaseCommand

from geo.models import Country, District, Province, Ward

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Nguồn: Campuchia từ NCDD gazetteer (github.com/RathanakSreang/cambodia-gazetteer, dừng ở cấp Khum/
# Sangkat — tương đương Phường/Xã, bỏ qua cấp Phum/village vì model chỉ có 3 cấp); Lào từ
# open-admin-data/laos-administrative-divisions (Lào chỉ có 3 cấp thật: Tỉnh/Huyện/Bản, nên "Ward"
# ở đây chính là Bản/village). Tên dùng bản Latin/English cho dễ đọc, không dùng chữ Khmer/Lào gốc.
FILES = {"KH": "kh_divisions.json", "LA": "la_divisions.json"}


class Command(BaseCommand):
    help = "Nhập dữ liệu Tỉnh/Thành - Quận/Huyện - Phường/Xã của Campuchia và Lào."

    def handle(self, *args, **options):
        for code, filename in FILES.items():
            country = Country.objects.get(code=code)
            # Idempotent, giống import_vn_divisions — bỏ qua nếu đã nhập rồi.
            if Province.objects.filter(country=country).exists():
                self.stdout.write(f"Dữ liệu hành chính {country.name}: đã có sẵn")
                continue

            data = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))

            province_count = district_count = ward_count = 0
            for p in data:
                province = Province.objects.create(
                    country=country, name=p["name"], code=str(p["code"]),
                    division_type=p.get("division_type", ""),
                )
                province_count += 1
                districts = [
                    District(
                        province=province, name=d["name"], code=str(d["code"]),
                        division_type=d.get("division_type", ""),
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
                                division_type=w.get("division_type", ""),
                            )
                        )
                Ward.objects.bulk_create(wards)
                ward_count += len(wards)

            self.stdout.write(
                f"{country.name}: đã nhập {province_count} tỉnh/thành, {district_count} quận/huyện, "
                f"{ward_count} phường/xã"
            )
