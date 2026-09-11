from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Tạo sẵn các nhóm quyền: Quản lý, Nhân viên kinh doanh, Nhân sự, Kế toán, Cung ứng"

    def handle(self, *args, **options):
        for name in (
            settings.GROUP_MANAGER, settings.GROUP_SALES, settings.GROUP_HR,
            settings.GROUP_ACCOUNTING, settings.GROUP_SUPPLY,
        ):
            _, created = Group.objects.get_or_create(name=name)
            status = "đã tạo" if created else "đã có sẵn"
            self.stdout.write(f"Nhóm '{name}': {status}")
