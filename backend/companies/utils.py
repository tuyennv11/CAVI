from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from accounts.roles import is_manager

from .models import Company

ACTIVE_COMPANY_HEADER = "HTTP_X_COMPANY_ID"  # request.META key cho header "X-Company-Id"


def get_active_company(request):
    """Công ty đang được thao tác cho request này — mọi ViewSet cần lọc dữ liệu theo công ty đều
    gọi hàm này (thường qua CompanyScopedMixin, xem mixins.py) thay vì tự đọc header tay.

    - Có header "X-Company-Id": phải hợp lệ (tồn tại, đang hoạt động) và user phải thuộc công ty đó
      — trừ is_manager (Quản lý) được chọn bất kỳ công ty nào, giữ đúng nghĩa "full access" đã áp
      dụng ở mọi nơi khác trong hệ thống.
    - Không có header: nếu user chỉ thuộc đúng 1 công ty thì tự dùng luôn công ty đó (đa số nhân sự
      chỉ làm 1 công ty, không nên bắt phải chọn) — nếu thuộc 0 hoặc từ 2 công ty trở lên (kể cả
      is_manager, vì Quản lý không có "công ty mặc định" rõ ràng) thì báo lỗi yêu cầu chọn rõ.
    """
    company_id = request.META.get(ACTIVE_COMPANY_HEADER)
    manager = is_manager(request.user)

    if company_id:
        try:
            company = Company.objects.get(pk=company_id, is_active=True)
        except (Company.DoesNotExist, ValueError):
            raise NotFound("Công ty không hợp lệ.")
        if not manager and not request.user.profile.companies.filter(pk=company.pk).exists():
            raise PermissionDenied("Bạn không thuộc công ty này.")
        return company

    if manager:
        raise ValidationError("Thiếu công ty đang thao tác (X-Company-Id) — Quản lý cần chọn rõ.")

    memberships = list(request.user.profile.companies.filter(is_active=True))
    if len(memberships) == 1:
        return memberships[0]
    if not memberships:
        raise PermissionDenied("Tài khoản chưa được gán vào công ty nào.")
    raise ValidationError("Bạn thuộc nhiều công ty — cần chọn rõ công ty đang thao tác (X-Company-Id).")
