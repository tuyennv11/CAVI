import json
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from companyhub.ingestion import commit_import, prepare


class Command(BaseCommand):
    help = "Validate a Drive export; --commit imports to the isolated local TEST only."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--source-id", required=True)
        parser.add_argument("--title", required=True)
        parser.add_argument("--account", required=True)
        parser.add_argument("--category", choices=["employees", "payroll", "commission", "fund_policy", "fund_data", "workflow", "guidance", "insurance", "leave_data", "other"], required=True)
        parser.add_argument("--period", default="")
        parser.add_argument("--commit", action="store_true")

    def handle(self, *args, **options):
        target = Path(settings.DATABASES["default"]["NAME"]).resolve()
        expected = (settings.BASE_DIR / ".preview" / "db.sqlite3").resolve()
        if not getattr(settings, "COMPANY_HUB_ENABLED", False) or target != expected:
            raise CommandError("Chỉ nhập vào database TEST biệt lập; từ chối database khác.")
        if options["commit"] and not (settings.BASE_DIR / ".preview" / "secret-key").is_file():
            raise CommandError("Cần khóa ký TEST riêng trước khi nhập dữ liệu thật.")
        keys = ["source_id", "title", "account", "category", "period"]
        try:
            prepared = prepare(options["path"], {key: options[key] for key in keys})
        except (ValueError, KeyError, StopIteration) as error:
            raise CommandError(f"Nguồn không phù hợp cấu trúc đã kiểm chứng: {error}") from None
        created = False
        if options["commit"]:
            # Archive inputs outside MEDIA_ROOT, immutable by content hash; never served statically.
            private = settings.BASE_DIR / ".preview" / "company-sources"
            private.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(private, 0o700)
            archive = private / (prepared["source"]["digest"] + Path(options["path"]).suffix.lower())
            if not archive.exists():
                with archive.open("xb") as output, open(options["path"], "rb") as source:
                    os.chmod(archive, 0o600)
                    shutil.copyfileobj(source, output)
            _, created = commit_import(prepared)
            os.chmod(target, 0o600)
        self.stdout.write(json.dumps({"committed": options["commit"], "new_version": created,
                                      "employee_rows": len(prepared["employees"]), "payroll_rows": len(prepared["payroll"]),
                                      "source_errors": len(prepared["source"]["issues"])}, ensure_ascii=False))
