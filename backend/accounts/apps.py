from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from config import admin_site  # noqa: F401 — sắp xếp lại trang admin theo luồng nghiệp vụ.

        # Nhãn mặc định "First name"/"Last name" của Django dễ khiến người nhập liệu điền theo thứ
        # tự phương Tây (Tên trước, Họ sau) — đổi nhãn rõ theo tiếng Việt để field first_name luôn
        # chứa Họ (và tên đệm), last_name luôn chứa Tên, ghép lại đúng thứ tự "Họ Tên" khi hiển thị
        # qua get_full_name() (vd "Nguyễn Vũ Tuyên").
        from django.contrib.auth.models import User

        User._meta.get_field("first_name").verbose_name = "Họ (và tên đệm)"
        User._meta.get_field("last_name").verbose_name = "Tên"

        # Hiện tên thật (vd "Nguyễn Vũ Tuyên") thay vì tên đăng nhập ở MỌI nơi User bị tham chiếu
        # dạng khoá ngoại (cột "Người tạo"/"Người chốt giá"/"Người thực hiện"... lúc xuất Excel,
        # dropdown chọn trong admin...) — cùng nguyên tắc với hr.Profile.__str__ (xem hr/models.py).
        def _user_str(self):
            return self.get_full_name() or self.username

        User.__str__ = _user_str
