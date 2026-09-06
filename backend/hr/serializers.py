from rest_framework import serializers

from .models import AttendanceRecord, LeaveBalance, Profile


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "username", "full_name", "email", "company_code", "job_title"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class LeaveBalanceSerializer(serializers.ModelSerializer):
    total_available = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "year",
            "annual_current",
            "annual_carried",
            "bonus_current",
            "bonus_carried",
            "bonus_pending",
            "total_available",
        ]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = ["id", "date", "checked_in_at", "note"]
        read_only_fields = ["date", "checked_in_at"]
