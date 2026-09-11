"""Tiện ích dùng chung cho các trang admin — hiện tại chỉ có `linked_fk()`."""

from django.urls import reverse
from django.utils.html import format_html


def linked_fk(obj):
    """Hiển thị 1 field khoá ngoại dạng link bấm được, dẫn thẳng tới trang sửa của bản ghi liên
    quan — để thấy rõ 2 bảng đang nối với nhau qua đâu (bấm vào là qua thẳng bên kia), thay vì chỉ
    hiện tên suông không biết bấm vào đâu."""
    if obj is None:
        return "—"
    url = reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    return format_html('<a href="{}">{}</a>', url, str(obj))
