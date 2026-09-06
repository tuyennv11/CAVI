from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.roles import is_manager

from .models import AttendanceRecord, LeaveBalance, Profile
from .serializers import AttendanceRecordSerializer, LeaveBalanceSerializer, ProfileSerializer


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = LeaveBalance.objects.all()
        user_id = self.request.query_params.get("user")
        if is_manager(self.request.user) and user_id:
            return qs.filter(user_id=user_id)
        if is_manager(self.request.user) and not user_id:
            return qs.filter(user=self.request.user)
        return qs.filter(user=self.request.user)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AttendanceRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        today = timezone.localdate()
        obj, created = AttendanceRecord.objects.get_or_create(
            user=self.request.user, date=today, defaults={"note": serializer.validated_data.get("note", "")}
        )
        serializer.instance = obj
