from django.contrib import admin

from .models import Country, District, Province, Ward


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country", "division_type")
    list_filter = ("country",)
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "province", "division_type")
    list_filter = ("province__country",)
    search_fields = ("name",)
    # Cần cho autocomplete_fields ở nơi khác (vd hr.ProfileAdmin) tìm nhanh trong 696 quận/huyện
    # thay vì hiện cả danh sách trong 1 dropdown khổng lồ.
    autocomplete_fields = ["province"]


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "district", "division_type")
    list_filter = ("district__province",)
    search_fields = ("name",)
    # Cần cho autocomplete_fields ở nơi khác tìm nhanh trong hơn 10.000 phường/xã.
    autocomplete_fields = ["district"]
