from django.core.management.base import BaseCommand, CommandError

from companies.demo_seed import SEED_USERS, seed_synthetic_data


class Command(BaseCommand):
    help = "Tạo một lần bộ dữ liệu giả trên database PostgreSQL CAVI TEST trống, không thay dữ liệu đã có."

    def add_arguments(self, parser):
        parser.add_argument("--confirm-isolated-test-database", action="store_true", help="Chỉ xác nhận sau khi đối chiếu DB/volumes và mạng TEST riêng.")

    def handle(self, *args, **options):
        if not options["confirm_isolated_test_database"]:
            raise CommandError("Cần --confirm-isolated-test-database sau khi xác minh tách biệt. Không có thay đổi nào được thực hiện.")
        created = seed_synthetic_data()
        if not created:
            self.stdout.write("Bộ mẫu đã tồn tại. Giữ nguyên dữ liệu anh đã sửa; không đặt lại tài khoản hoặc mật khẩu.")
            return
        self.stdout.write(self.style.SUCCESS("Đã tạo bộ dữ liệu GIẢ: 2 công ty thử, 5 người dùng, 3 khách, 5 đơn, 7 công việc, 2 KPI, 2 thông báo."))
        self.stdout.write("Tất cả tài khoản mới đều KHÔNG CÓ mật khẩu đăng nhập. Không có password mặc định.")
        self.stdout.write("Tài khoản thử: " + ", ".join(SEED_USERS))
        self.stdout.write("Người triển khai đặt mật khẩu riêng cho tài khoản cần thử bằng changepassword trên đúng TEST, không dùng mật khẩu HR/Apple/production.")
