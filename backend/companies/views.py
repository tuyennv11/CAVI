from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """Danh sách công ty — dùng để gán Nhân sự/tick Đối tác thuộc công ty nào (không giới hạn theo
    công ty người xem đang thuộc về, vì đây là thao tác gán/tick cho NGƯỜI/ĐỐI TƯỢNG khác, không
    phải xem dữ liệu nghiệp vụ của công ty mình)."""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    queryset = Company.objects.filter(is_active=True)
    pagination_class = None
