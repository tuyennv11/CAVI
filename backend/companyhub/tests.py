from copy import deepcopy
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .calculations import FUND_REVIEWED_DIGEST, FUND_SOURCE_ID, fund_draft, payroll_components
from .ingestion import commit_import, payroll_rows, roster_rows
from .models import EmployeeMaster, PayrollRecord, SourceSnapshot


def cell(value, **extra):
    return {"value": value, **extra}


def fake_roster():
    return {"kind": "workbook", "sheets": [{"title": "THÔNG TIN NV", "rows": [
        {"row": 5, "cells": {"A": cell("CÔNG TY"), "C": cell("MSNV"), "D": cell("HỌ VÀ TÊN"), "E": cell("Còn làm"), "H": cell("PHÒNG")}},
        {"row": 6, "cells": {"A": cell("SYNTHETIC"), "C": cell("FAKE-001"), "D": cell("Nhân viên giả định"), "E": cell("x"), "H": cell("Kho")}},
        {"row": 7, "cells": {"C": cell("FAKE-002"), "D": cell("Hồ sơ giả định 2")}},
    ]}]}


def prepared_source(digest="a" * 64):
    content = fake_roster()
    return {"source": {"source_id": "synthetic-roster", "digest": digest, "title": "Danh sách giả định", "account": "synthetic@example.test",
                       "category": "employees", "period": "", "content": content, "issues": []}, "employees": roster_rows(content), "payroll": []}


def example_fund():
    return {"department": "operations", "period": "2025-11", "fund_period": "2025-10", "cavi_fund": "20000000",
            "livi_fund": "15000000", "service_fund": "10000000", "minimum_income": "15000000",
            "other_personnel_costs": "1050000", "proposed_bonus": "19950000"}


@override_settings(COMPANY_HUB_ENABLED=True)
class ImportTests(TestCase):
    def test_import_is_idempotent_and_does_not_create_logins_or_profiles(self):
        source, created = commit_import(prepared_source())
        self.assertTrue(created)
        again, created = commit_import(prepared_source())
        self.assertFalse(created)
        self.assertEqual(source.id, again.id)
        self.assertEqual(EmployeeMaster.objects.count(), 2)
        self.assertEqual(User.objects.count(), 0)

    def test_import_keeps_versions(self):
        commit_import(prepared_source())
        commit_import(prepared_source("b" * 64))
        self.assertEqual(SourceSnapshot.objects.count(), 2)
        self.assertEqual(EmployeeMaster.objects.count(), 4)

    def test_blank_company_and_status_not_inferred(self):
        records = roster_rows(fake_roster())
        self.assertEqual(records[1]["source_company"], "")
        self.assertEqual(records[1]["status"], "unconfirmed")
        self.assertEqual(records[0]["status"], "source_active")

    def test_duplicate_source_code_kept_and_flagged(self):
        content = fake_roster()
        content["sheets"][0]["rows"].append({**deepcopy(content["sheets"][0]["rows"][1]), "row": 8})
        records = roster_rows(content)
        self.assertEqual(len(records), 3)
        self.assertTrue(any("trùng" in issue for issue in records[0]["issues"]))

    def test_active_and_resignation_conflict(self):
        content = fake_roster()
        content["sheets"][0]["rows"][1]["cells"]["CA"] = cell("2026-01-01")
        self.assertEqual(roster_rows(content)[0]["status"], "conflict")

    def test_changed_header_or_missing_code_fails_closed(self):
        content = fake_roster()
        content["sheets"][0]["rows"][0]["cells"]["C"] = cell("unexpected")
        with self.assertRaises(ValueError):
            roster_rows(content)
        content = fake_roster()
        del content["sheets"][0]["rows"][1]["cells"]["C"]
        with self.assertRaises(ValueError):
            roster_rows(content)

    def test_command_refuses_nonisolated_database_before_read(self):
        with self.assertRaises(CommandError), patch("companyhub.management.commands.import_company_source.prepare") as prepare:
            call_command("import_company_source", "/does-not-exist.xlsx", source_id="fake", title="Fake", account="fake@example.test", category="employees", commit=True)
        prepare.assert_not_called()

    def test_dry_run_does_not_write(self):
        target = str(settings.BASE_DIR / ".preview" / "db.sqlite3")
        with patch.dict(settings.DATABASES["default"], {"NAME": target}), patch("companyhub.management.commands.import_company_source.prepare", return_value=prepared_source()):
            output = StringIO()
            call_command("import_company_source", "/synthetic.xlsx", source_id="fake", title="Fake", account="fake@example.test", category="employees", stdout=output)
            self.assertIn('"committed": false', output.getvalue())
        self.assertEqual(SourceSnapshot.objects.count(), 0)

    def test_atomic_failure_rolls_back_source(self):
        invalid = prepared_source()
        invalid["employees"][1]["name"] = None
        with self.assertRaises(IntegrityError):
            commit_import(invalid)
        self.assertEqual(SourceSnapshot.objects.count(), 0)


class CalculationTests(TestCase):
    def test_fund_matches_policy_example(self):
        result = fund_draft(example_fund())
        self.assertEqual(result["maximum_additional_bonus"], "19950000")
        self.assertEqual(result["personnel_ceiling"], "36000000")
        self.assertTrue(result["within_ceiling"])
        self.assertTrue(result["approval_required"])
        self.assertFalse(result["payment_created"])

    def test_missing_zero_invalid_and_excluded_departments(self):
        for value in [None, "", "NaN", "Infinity", "-1", True, "abc"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                fund_draft({**example_fund(), "cavi_fund": value})
        self.assertEqual(fund_draft({**example_fund(), "proposed_bonus": "0"})["excess"], "0")
        for dept in ["sales", "supply", "guess"]:
            with self.assertRaises(ValueError):
                fund_draft({**example_fund(), "department": dept})

    def test_fund_period_and_negative_headroom(self):
        with self.assertRaises(ValueError):
            fund_draft({**example_fund(), "fund_period": "2025-09"})
        with self.assertRaises(ValueError):
            fund_draft({**example_fund(), "period": "2025-10", "fund_period": "2025-09"})
        result = fund_draft({**example_fund(), "minimum_income": "40000000", "proposed_bonus": "0"})
        self.assertEqual(result["maximum_additional_bonus"], "0")
        self.assertFalse(result["within_ceiling"])
        self.assertEqual(result["excess"], "5050000")

    def test_payroll_only_exact_verified_row_formula(self):
        cells = {"I": cell(21000000), "N": cell(21), "S": cell(20), "AF": cell(20000000, formula="=I7/N7*S7")}
        result = payroll_components(cells, 7)
        self.assertEqual(result["components"][0]["amount"], "20000000")
        self.assertEqual(result["components"][0]["difference"], "0")
        self.assertIsNone(result["net_pay"])
        self.assertIsNone(result["components"][1]["amount"])
        cells["AF"]["formula"] = "=I7/N7*S7*0.85"
        self.assertIsNone(payroll_components(cells, 7)["components"][0]["amount"])
        cells["AF"]["formula"] = "=I8/N7*S7"
        self.assertIsNone(payroll_components(cells, 7)["components"][0]["amount"])

    def test_zero_standard_days_and_broken_input_cannot_calculate(self):
        cells = {"I": cell(1000000), "N": cell(0), "S": cell(20), "AF": cell(None, formula="=I7/N7*S7")}
        self.assertIsNone(payroll_components(cells, 7)["components"][0]["amount"])
        cells["N"] = cell(21)
        cells["I"] = cell("#REF!", error="#REF!")
        self.assertIsNone(payroll_components(cells, 7)["components"][0]["amount"])

    def test_payroll_audit_flags_bad_references(self):
        content = {"sheets": [{"title": "LƯƠNG T05.2026", "rows": [
            {"row": 5, "cells": {"B": cell("MÃ SỐ NV"), "BC": cell("THỰC LĨNH")}},
            {"row": 7, "cells": {"B": cell("FAKE"), "C": cell("Giả định"), "AY": cell(None, formula="=AT7-#REF!"),
                                  "AZ": cell(0, formula="=AW7*5%"), "BC": cell(0, formula="=AT7-AV7"), "AT": cell(0, formula="=AF7+AN7")}},
        ]}]}
        self.assertEqual(len(payroll_rows(content, "2026-05")[0]["issues"]), 4)


@override_settings(COMPANY_HUB_ENABLED=True, COMPANY_HUB_OWNER_USERNAME="synthetic-owner")
class PrivacyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user("synthetic-owner", is_superuser=True)
        self.staff = User.objects.create_user("synthetic-staff")
        self.source, _ = commit_import(prepared_source())
        self.employee = EmployeeMaster.objects.first()

    def test_all_endpoints_require_owner_and_are_not_cached(self):
        urls = ["", "employees/", f"employees/{self.employee.id}/", "payroll/", "payroll/999/", f"sources/{self.source.id}/"]
        for user in [None, self.staff]:
            self.client.force_authenticate(user)
            for path in urls:
                with self.subTest(user=user, path=path):
                    response = self.client.get("/api/company-hub/" + path)
                    self.assertIn(response.status_code, [401, 403])
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertNotIn("Nhân viên giả định", str(response.data))
            self.assertIn(self.client.post("/api/company-hub/fund-calculate/", example_fund()).status_code, [401, 403])

    def test_manager_group_does_not_grant_access(self):
        self.staff.groups.add(Group.objects.create(name=settings.GROUP_MANAGER))
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/company-hub/").status_code, 403)

    def test_other_copied_admin_does_not_gain_access_to_real_imports(self):
        self.staff.is_superuser = True
        self.staff.save()
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/company-hub/").status_code, 403)

    def test_owner_gets_records_without_cross_session_mutation(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/company-hub/employees/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("fields", response.data["results"][0])
        self.assertEqual(self.client.post("/api/company-hub/employees/", {}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/company-hub/employees/{self.employee.id}/").status_code, 405)

    def test_source_versions_dont_double_count_or_serve_old_record(self):
        commit_import(prepared_source("b" * 64))
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/company-hub/").data["employee_count"], 2)
        self.assertEqual(self.client.get(f"/api/company-hub/employees/{self.employee.id}/").status_code, 404)

    def test_invalid_page_and_missing_source(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/company-hub/employees/?page=oops").status_code, 400)
        self.assertEqual(self.client.get("/api/company-hub/employees/?page=0").status_code, 400)
        self.assertEqual(self.client.get("/api/company-hub/sources/99999/").status_code, 404)

    def test_fund_requires_imported_policy_and_never_persists_payment(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post("/api/company-hub/fund-calculate/", example_fund()).status_code, 400)
        SourceSnapshot.objects.create(source_id=FUND_SOURCE_ID, digest=FUND_REVIEWED_DIGEST, title="Synthetic policy", account="test", category="fund_policy")
        before = PayrollRecord.objects.count()
        response = self.client.post("/api/company-hub/fund-calculate/", example_fund())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["maximum_additional_bonus"], "19950000")
        self.assertEqual(PayrollRecord.objects.count(), before)
        SourceSnapshot.objects.create(source_id=FUND_SOURCE_ID, digest="d" * 64, title="Synthetic replacement policy", account="test", category="fund_policy")
        self.assertEqual(self.client.post("/api/company-hub/fund-calculate/", example_fund()).status_code, 400)

    @override_settings(COMPANY_HUB_ENABLED=False)
    def test_disabled_mode_even_owner_denied(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/company-hub/").status_code, 403)

    def test_old_public_preview_signing_key_rejected(self):
        import jwt
        from rest_framework_simplejwt.backends import TokenBackend
        from rest_framework_simplejwt.tokens import RefreshToken
        # No dependency on a real local secret or imported company data in tests.
        backend = TokenBackend(algorithm="HS256", signing_key="synthetic-test-only-key-not-a-live-credential")
        with patch("rest_framework_simplejwt.state.token_backend", backend):
            token = RefreshToken.for_user(self.owner).access_token
            self.client.credentials(HTTP_AUTHORIZATION="Bearer " + jwt.encode(token.payload, "cavi-local-preview-only-not-for-deployment", algorithm="HS256"))
            self.assertEqual(self.client.get("/api/company-hub/").status_code, 401)
            self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token))
            self.assertEqual(self.client.get("/api/company-hub/").status_code, 200)
