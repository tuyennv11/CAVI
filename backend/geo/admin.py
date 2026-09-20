from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from config.admin_import_export import ExcelModelResource

from .models import Country, District, Province, Ward


class CountryResource(ExcelModelResource):
    class Meta:
        model = Country


class ProvinceResource(ExcelModelResource):
    class Meta:
        model = Province


class DistrictResource(ExcelModelResource):
    class Meta:
        model = District


class WardResource(ExcelModelResource):
    class Meta:
        model = Ward


@admin.register(Country)
class CountryAdmin(ImportExportModelAdmin):
    resource_classes = [CountryResource]
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Province)
class ProvinceAdmin(ImportExportModelAdmin):
    resource_classes = [ProvinceResource]
    list_display = ("name", "code", "country", "division_type")
    list_filter = ("country",)
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(ImportExportModelAdmin):
    resource_classes = [DistrictResource]
    list_display = ("name", "code", "province", "division_type")
    list_filter = ("province__country",)
    search_fields = ("name",)
    # Cần cho autocomplete_fields ở nơi khác (vd hr.ProfileAdmin) tìm nhanh trong 696 quận/huyện
    # thay vì hiện cả danh sách trong 1 dropdown khổng lồ.
    autocomplete_fields = ["province"]


@admin.register(Ward)
class WardAdmin(ImportExportModelAdmin):
    resource_classes = [WardResource]
    list_display = ("name", "code", "district", "division_type")
    list_filter = ("district__province",)
    search_fields = ("name",)
    # Cần cho autocomplete_fields ở nơi khác tìm nhanh trong hơn 10.000 phường/xã.
    autocomplete_fields = ["district"]
