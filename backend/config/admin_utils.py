"""Tiện ích dùng chung cho các trang admin — hiện tại chỉ có `truncated()`."""

from django.utils.html import format_html
from django.utils.text import Truncator


def truncated(text, length=40):
    """Cắt ngắn text dài cho gọn trên bảng danh sách (không vỡ layout), nhưng vẫn rê chuột vào là
    xem được đầy đủ — giống ô có chú thích (comment) trong Excel — thay vì phải bấm vào từng dòng."""
    if not text:
        return "—"
    short = Truncator(text).chars(length)
    return format_html('<span title="{}">{}</span>', text, short)
