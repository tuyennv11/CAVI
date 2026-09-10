from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Country, District, Province, Ward
from .serializers import CountrySerializer, DistrictSerializer, ProvinceSerializer, WardSerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    queryset = Country.objects.all()
    pagination_class = None


class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProvinceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Province.objects.all()
    filterset_fields = ["country"]
    search_fields = ["name"]
    pagination_class = None


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DistrictSerializer
    permission_classes = [IsAuthenticated]
    queryset = District.objects.all()
    filterset_fields = ["province"]
    search_fields = ["name"]
    pagination_class = None


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WardSerializer
    permission_classes = [IsAuthenticated]
    queryset = Ward.objects.all()
    filterset_fields = ["district"]
    search_fields = ["name"]
    pagination_class = None
