from rest_framework import serializers

from .models import (
    AttendanceRecord,
    BonusPenaltyRecord,
    CompensationRecord,
    EmergencyContact,
    EmployeeDocument,
    LeaveBalance,
    Profile,
)

# Field do Quản lý quyết định qua trang quản lý nhân sự — nhân viên không tự sửa được trên trang
# "Hồ sơ cá nhân" của chính mình.
MANAGER_ONLY_FIELDS = [
    "employee_code", "job_title", "level", "manager", "work_location", "job_description",
    "contract_type", "contract_started_at", "contract_expires_at", "department",
    "hired_at", "resigned_at", "work_status", "employment_type",
]

PROFILE_FIELDS = [
    "id",
    "user",
    "username",
    "full_name",
    "email",
    "employee_code",
    "preferred_name",
    "gender",
    "avatar",
    "company_code",
    "job_title",
    "level",
    "manager",
    "manager_name",
    "work_location",
    "job_description",
    "contract_type",
    "contract_started_at",
    "contract_expires_at",
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
    "resigned_at",
    "work_status",
    "employment_type",
]


class BaseProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    manager_name = serializers.SerializerMethodField()
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)
    province_name = serializers.CharField(source="province.name", read_only=True, default=None)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)

    class Meta:
        model = Profile
        fields = PROFILE_FIELDS

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_manager_name(self, obj):
        if not obj.manager:
            return None
        return obj.manager.get_full_name() or obj.manager.username


class ProfileSerializer(BaseProfileSerializer):
    """Dùng cho trang quản lý nhân sự (Quản lý xem/sửa hồ sơ người khác) — sửa được mọi field
    trừ employee_code (tự sinh, không cho sửa tay)."""

    class Meta(BaseProfileSerializer.Meta):
        read_only_fields = ["user", "employee_code"]


class MyProfileSerializer(BaseProfileSerializer):
    """Dùng cho trang "Hồ sơ cá nhân" (nhân viên tự xem/sửa hồ sơ của chính mình) — các field do
    Quản lý quyết định (chức vụ, phòng ban, quản lý trực tiếp, hợp đồng, tình trạng làm việc...)
    không cho tự sửa."""

    class Meta(BaseProfileSerializer.Meta):
        read_only_fields = ["user", "employee_code"] + MANAGER_ONLY_FIELDS


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = [
            "id", "profile", "doc_type", "title", "number", "issued_at", "issued_place",
            "expires_at", "file", "note", "created_by", "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "profile", "name", "relationship", "phone", "address", "note"]


class CompensationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationRecord
        fields = [
            "id", "profile", "effective_date", "base_salary", "allowance", "insurance_base",
            "bank_name", "bank_account", "payment_method", "note", "created_by", "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class BonusPenaltyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusPenaltyRecord
        fields = ["id", "profile", "record_type", "amount", "reason", "effective_date", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


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
