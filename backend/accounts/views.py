from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer, UserSerializer

User = get_user_model()


class MeView(APIView):
    """Trả thông tin người đang đăng nhập + vai trò, để frontend hiện đúng giao diện/quyền."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class UserListView(APIView):
    """Danh sách người dùng đang hoạt động — dùng để chọn Người thực hiện/Người phụ trách."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(is_active=True).order_by("username")
        return Response(UserSerializer(users, many=True).data)
