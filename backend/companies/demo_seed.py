"""Synthetic staging fixtures, deliberately unavailable for a copied/live DB."""

from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.utils import timezone

from crm.models import KPITarget, Notice, Order, OrderItem, Partner, Task
from finance.models import OrderCost, OrderFinance, OrderPayment

from .models import Company

SEED_MARKER = "CAVI_SYNTHETIC_FIXTURES_V1"
COMPANY_CODE = "CAVI_TEST"
OTHER_COMPANY_CODE = "TRADE_TEST"
SEED_USERS = ("cavi-test-owner", "cavi-test-sales", "cavi-test-sales-2", "cavi-test-accountant", "cavi-test-other")


def require_isolated_staging_database():
    database = connection.settings_dict
    expected = {"ENGINE": "django.db.backends.postgresql", "NAME": "cavi_test", "USER": "cavi_test", "HOST": "test-db", "PORT": "5432"}
    if (getattr(settings, "SETTINGS_MODULE", "") != "config.staging_settings"
            or getattr(settings, "CAVI_ENVIRONMENT", "") != "preview"
            or settings.ROOT_URLCONF != "config.staging_urls" or settings.DEBUG
            or any(str(database.get(key, "")) != value for key, value in expected.items())):
        raise CommandError("Chỉ tạo dữ liệu giả trên PostgreSQL TEST riêng với config.staging_settings. Không chạy trên production hoặc DB preview đã copy.")
    # Validate the actual connection, not just a settings label. No writes here.
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        if cursor.fetchone() != ("cavi_test", "cavi_test"):
            raise CommandError("Kết nối thực tế không phải database/user TEST. Dừng trước khi ghi.")


def _check_empty_business_database():
    if get_user_model().objects.exists():
        raise CommandError("Database đã có tài khoản. Không trộn dữ liệu mẫu vào bản copy hoặc dữ liệu đang dùng.")
    for app_label in ("crm", "hr", "ops", "inventory", "finance", "approvals"):
        for model in apps.get_app_config(app_label).get_models():
            if model.objects.exists():
                raise CommandError(f"Database đã có dữ liệu trong {model._meta.label}. Không nhập mẫu, không xóa hay thay thế dữ liệu đó.")
    # Công ty CAVI/AVI đã bị gộp/xoá hẳn (companies.migrations.0004) — từ giờ chỉ còn đúng 1 công ty
    # trống từ migration: LIVI.
    baseline = {"LIVI": ("LIVI", "trading")}
    for company in Company.objects.all():
        if ((company.name, company.business_type) != baseline.get(company.code)
                or any((company.legal_name, company.tax_code, company.hotline, company.address, company.logo))):
            raise CommandError("Có công ty ngoài định nghĩa trống từ migration. Không nhập dữ liệu mẫu vào database này.")


def seed_synthetic_data():
    """Create once, atomically. Reruns never reset edits, passwords or due dates."""
    require_isolated_staging_database()
    return _create_synthetic_data()


@transaction.atomic
def _create_synthetic_data():
    existing = Company.objects.filter(code=COMPANY_CODE).first()
    if existing:
        if existing.legal_name != SEED_MARKER:
            raise CommandError("Mã công ty TEST đã được dùng bởi dữ liệu khác. Không ghi đè.")
        return False
    _check_empty_business_database()

    company = Company.objects.create(code=COMPANY_CODE, name="CAVI · DỮ LIỆU THỬ", business_type="transport", legal_name=SEED_MARKER)
    other = Company.objects.create(code=OTHER_COMPANY_CODE, name="THƯƠNG MẠI · DỮ LIỆU THỬ", business_type="trading", legal_name=SEED_MARKER)
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in (
        settings.GROUP_MANAGER, settings.GROUP_SALES, settings.GROUP_HR, settings.GROUP_ACCOUNTING, settings.GROUP_SUPPLY,
    )}

    def user(username, label, department, memberships, group, owner=False):
        result = get_user_model().objects.create_user(
            username=username, password=None, first_name=f"{label} (TEST)", email="",
            is_staff=owner, is_superuser=owner,
        )
        result.groups.add(groups[group])
        profile = result.profile
        profile.preferred_name = result.first_name
        profile.department = department
        profile.job_title = label
        profile.job_description = "Hồ sơ hoàn toàn giả để thử app; không phải nhân sự thật."
        profile.work_location = "Kho mô phỏng — không phải điểm nhận hàng thật"
        profile.save()
        profile.companies.add(*memberships)
        return result

    owner = user(SEED_USERS[0], "Chủ doanh nghiệp", "management", [company, other], settings.GROUP_MANAGER, owner=True)
    sales = user(SEED_USERS[1], "Kinh doanh A", "sales", [company], settings.GROUP_SALES)
    colleague = user(SEED_USERS[2], "Kinh doanh B", "sales", [company], settings.GROUP_SALES)
    accountant = user(SEED_USERS[3], "Kế toán", "accounting", [company], settings.GROUP_ACCOUNTING)
    other_sales = user(SEED_USERS[4], "Kinh doanh công ty khác", "sales", [other], settings.GROUP_SALES)

    def partner(label, assigned, target):
        result = Partner.objects.create(name=f"[TEST] {label}", assigned_to=assigned, note="Khách hàng giả. Không liên hệ, không giao hàng, không thu tiền.")
        result.companies.add(target)
        return result

    customer = partner("Khách gửi hàng mẫu A", sales, company)
    colleague_customer = partner("Khách do kinh doanh B phụ trách", colleague, company)
    other_customer = partner("Khách thương mại độc lập", other_sales, other)
    now = timezone.localtime()
    order_specs = [
        ("Nhận 12 thùng hàng mẫu", customer, sales, company, Order.Status.PENDING_RECEIPT, "12", "150000", "90000"),
        ("Đối chiếu số lượng hàng đã nhận", customer, sales, company, Order.Status.PENDING_CONFIRMATION, "10", "180000", "110000"),
        ("Theo dõi chuyến đang vận chuyển", colleague_customer, colleague, company, Order.Status.PROCESSING, "20", "160000", "95000"),
        ("Đơn mẫu đã hoàn tất — còn công nợ", customer, sales, company, Order.Status.DONE, "15", "200000", "120000"),
        ("Đơn công ty khác — kiểm tra phân quyền", other_customer, other_sales, other, Order.Status.NEW, "8", "100000", "70000"),
    ]
    for title, customer_row, assigned, target, status, quantity, price, cost in order_specs:
        order = Order.objects.create(
            customer=customer_row, company=target, created_by=assigned, status=status,
            description=f"[TEST] {title}", note="Dữ liệu giả — không phát sinh vận chuyển hay thanh toán thật.",
            pickup_point="Điểm lấy mô phỏng A", delivery_point="Điểm giao mô phỏng B", weight_kg=Decimal("120"),
        )
        OrderItem.objects.create(order=order, description=f"[TEST] {title}", quantity=Decimal(quantity), unit_price=Decimal(price), unit_cost=Decimal(cost), actual_quantity=Decimal("9") if status == Order.Status.PENDING_CONFIRMATION else None)
        finance = OrderFinance.objects.get(order=order)
        finance.note = "Số tiền giả dùng thử giao diện; không phải sổ sách công ty."
        finance.save(update_fields=["note"])
        if status == Order.Status.DONE:
            OrderCost.objects.create(finance=finance, category=OrderCost.Category.PICKUP, amount=Decimal("200000"), created_by=accountant)
            OrderPayment.objects.create(finance=finance, payment_type=OrderPayment.PaymentType.COLLECTION, amount=Decimal("1000000"), recorded_by=accountant)

    for index, (title, offset, status, assignee, target) in enumerate([
        ("Duyệt cách hiển thị phiếu nhận hàng", 0, Task.Status.TODO, owner, company),
        ("Xem báo cáo công nợ mẫu", 1, Task.Status.TODO, owner, company),
        ("Xác nhận hàng thực nhận", 0, Task.Status.IN_PROGRESS, sales, company),
        ("Liên hệ khách mẫu đang quá hạn", -1, Task.Status.TODO, sales, company),
        ("Hoàn thành checklist giao hàng mẫu", -1, Task.Status.DONE, sales, company),
        ("Việc riêng kinh doanh B", 0, Task.Status.TODO, colleague, company),
        ("Việc công ty thương mại riêng", 0, Task.Status.TODO, other_sales, other),
    ]):
        Task.objects.create(title=f"[TEST] {title}", content="Nhiệm vụ mô phỏng, không cần liên hệ người thật.", company=target, assigned_to=assignee, created_by=owner, due_at=now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=offset), priority=Task.Priority.HIGH if index < 4 else Task.Priority.NORMAL, status=status)

    month = timezone.localdate()
    for target_user in (owner, sales):
        KPITarget.objects.create(user=target_user, company=company, year=month.year, month=month.month, revenue_target=Decimal("30000000"), new_customer_target=5, quote_target=12, order_target=10, task_target=20)
    for target in (company, other):
        Notice.objects.create(company=target, code="TEST-001", title="Đây là môi trường thử — không phải dữ liệu công ty", body="Mọi người dùng, khách hàng, lô hàng và số tiền tại đây đều là dữ liệu giả. Anh có thể thử thao tác để góp ý giao diện. Không tải hồ sơ nhân sự thật lên bản thử này.", created_by=owner)
    return True
