from rest_framework.routers import DefaultRouter

from .views import CountryViewSet, DistrictViewSet, ProvinceViewSet, WardViewSet

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("provinces", ProvinceViewSet, basename="province")
router.register("districts", DistrictViewSet, basename="district")
router.register("wards", WardViewSet, basename="ward")

urlpatterns = router.urls
