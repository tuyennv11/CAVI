from .utils import get_active_company


class CompanyScopedMixin:
    """Trộn vào ViewSet để lọc dữ liệu theo công ty đang thao tác — dùng 1 chỗ thay vì lặp lại logic
    đọc header/kiểm tra quyền ở mỗi ViewSet. Lọc theo công ty áp dụng TRƯỚC và ĐỘC LẬP với is_manager
    (Quản lý vẫn chỉ thấy đúng phạm vi công ty đang chọn, không phải thấy hết mọi công ty cùng lúc).

    `company_field`: tên field/đường dẫn lookup tới company trên model của ViewSet — vd "company"
    (field ngay trên model) hoặc "inquiry__company" (model nối gián tiếp qua Hỏi giá, không có field
    company riêng — xem PriceInquiryQuoteLineViewSet)."""

    company_field = "company"

    def get_active_company(self):
        if not hasattr(self, "_active_company"):
            self._active_company = get_active_company(self.request)
        return self._active_company

    def scope_by_company(self, queryset):
        return queryset.filter(**{self.company_field: self.get_active_company()})
