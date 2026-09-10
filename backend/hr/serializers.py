from rest_framework import serializers

from .models import AttendanceRecord, LeaveBalance, Profile


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)
    province_name = serializers.CharField(source="province.name", read_only=True, default=None)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "company_code",
            "job_title",
            "department",
            "phone",
            "date_of_birth",
            "id_number",
            "country",
            "country_name",
            "province",
            "province_name",
            "district",
            "district_name",
            "ward",
            "ward_name",
            "street_address",
            "hired_at",
            "employment_status",
        ]
        # Phòng ban/ngày vào làm/trạng thái làm việc do Quản lý quyết định qua trang quản trị,
        # không để nhân viên tự sửa lung tung trên trang Hồ sơ cá nhân của chính mình.
        read_only_fields = ["department", "hired_at", "employment_status"]

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
