from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from companies.models import Company
from crm.models import Partner, PriceInquiry, Quotation, QuotationLine
from notifications.models import Notification, PushOutbox
from .models import ApprovalRequest


@override_settings(CAVI_NOTIFICATIONS_ENABLED=True, ROOT_URLCONF="config.preview_urls")
class ApprovalNotificationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Synthetic Approval", code="SYN-APPROVAL", business_type="transport")
        self.other = Company.objects.create(name="Synthetic Approval Other", code="SYN-APP-OTHER", business_type="trading")
        users = get_user_model().objects
        self.manager = users.create_user("synthetic-approval-manager", is_staff=True)
        self.requester = users.create_user("synthetic-approval-requester")
        self.peer = users.create_user("synthetic-approval-peer")
        self.requester.profile.companies.add(self.company)
        self.peer.profile.companies.add(self.company)
        self.client = APIClient()
        self.as_user(self.manager)

    def as_user(self, user, company=None):
        self.client.force_authenticate(user)
        self.client.credentials(HTTP_X_COMPANY_ID=str((company or self.company).pk))

    def approval(self, **changes):
        return ApprovalRequest.objects.create(company=self.company, requested_by=self.requester,
            **{"request_type": "proposal", "title": "Synthetic private proposal", "amount": "200", **changes})

    def quotation(self, approval=None):
        partner = Partner.objects.create(name="Synthetic quotation customer", assigned_to=self.requester)
        partner.companies.add(self.company)
        inquiry = PriceInquiry.objects.create(company=self.company, customer=partner, floor_price=100, ceiling_price=150)
        obj = Quotation.objects.create(inquiry=inquiry, note="Synthetic previous note", pending_approval=approval,
            pending_snapshot={"note": "Synthetic new note", "lines": [{"item_name": "Synthetic new line", "quantity": "2", "price": "100"}]} if approval else None)
        QuotationLine.objects.create(quotation=obj, item_name="Synthetic previous line", quantity=1, price=100)
        return obj

    def test_failed_quote_application_cannot_leave_approved_request_or_partial_quote(self):
        approval = self.approval()
        quotation = self.quotation(approval)
        original_line = quotation.lines.get().pk
        with patch("crm.models.QuotationLine.objects.bulk_create", side_effect=RuntimeError("Synthetic write failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"/api/approval-requests/{approval.pk}/approve/")
        approval.refresh_from_db()
        quotation.refresh_from_db()
        self.assertEqual(approval.status, "pending")
        self.assertIsNone(approval.reviewed_at)
        self.assertEqual(quotation.pending_approval_id, approval.pk)
        self.assertEqual(quotation.note, "Synthetic previous note")
        self.assertEqual(quotation.lines.get().pk, original_line)
        self.assertEqual(Notification.objects.count(), 0)

    def test_new_request_notifies_reviewers_not_unrelated_colleagues(self):
        self.as_user(self.requester)
        response = self.client.post("/api/approval-requests/", {"request_type": "settlement", "title": "Synthetic settlement", "amount": "200", "currency": "VND"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        item = Notification.objects.get()
        self.assertEqual((item.kind, item.recipient_id), ("approval_submitted", self.manager.pk))
        self.assertEqual(PushOutbox.objects.get().state, "not_configured")
        self.as_user(self.peer)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)

    def test_approve_applies_quote_and_notifies_requester_once(self):
        approval = self.approval()
        quotation = self.quotation(approval)
        url = f"/api/approval-requests/{approval.pk}/approve/"
        self.assertEqual(self.client.post(url).status_code, 200)
        approval.refresh_from_db()
        quotation.refresh_from_db()
        reviewed_at = approval.reviewed_at
        new_line_id = quotation.lines.get().pk
        self.assertEqual(approval.status, "approved")
        self.assertIsNone(quotation.pending_snapshot)
        self.assertIsNone(quotation.pending_approval_id)
        self.assertEqual(quotation.lines.get().price, Decimal("100"))
        self.assertEqual((Notification.objects.get().kind, Notification.objects.get().recipient_id), ("approval_approved", self.requester.pk))
        self.assertEqual(self.client.post(url).status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.reviewed_at, reviewed_at)
        self.assertEqual(quotation.lines.get().pk, new_line_id)
        self.assertEqual(Notification.objects.count(), 1)

    def test_notification_failure_rolls_back_successful_quote_application(self):
        approval = self.approval()
        quotation = self.quotation(approval)
        old_line = quotation.lines.get().pk
        with patch("notifications.service.PushOutbox.objects.get_or_create", side_effect=RuntimeError("Synthetic outbox failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"/api/approval-requests/{approval.pk}/approve/")
        approval.refresh_from_db()
        quotation.refresh_from_db()
        self.assertEqual(approval.status, "pending")
        self.assertEqual(quotation.pending_approval_id, approval.pk)
        self.assertEqual(quotation.lines.get().pk, old_line)
        self.assertEqual(Notification.objects.count(), 0)

    def test_reject_and_mark_paid_have_distinct_safe_notifications(self):
        approval = self.approval()
        url = f"/api/approval-requests/{approval.pk}/reject/"
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(Notification.objects.filter(kind="approval_rejected").count(), 1)
        settlement = self.approval(request_type="settlement", status="approved")
        paid_url = f"/api/approval-requests/{settlement.pk}/mark_paid/"
        self.assertEqual(self.client.post(paid_url).status_code, 200)
        self.assertEqual(self.client.post(paid_url).status_code, 200)
        self.assertEqual(Notification.objects.filter(kind="approval_paid").count(), 1)
        self.assertEqual(self.client.post(f"/api/approval-requests/{approval.pk}/mark_paid/").status_code, 400)
        self.as_user(self.requester)
        data = self.client.get("/api/notifications/").data
        paid = next(item for item in data["results"] if item["kind"] == "approval_paid")
        self.assertIn("không phải xác nhận giao dịch ngân hàng", paid["body"])

    def test_cannot_override_reviewed_decisions_or_mutate_their_content(self):
        for status, action in [("approved", "reject"), ("rejected", "approve"), ("paid", "approve"), ("paid", "reject")]:
            approval = self.approval(status=status)
            self.assertEqual(self.client.post(f"/api/approval-requests/{approval.pk}/{action}/").status_code, 400)
            self.assertEqual(self.client.patch(f"/api/approval-requests/{approval.pk}/", {"amount": "999"}, format="json").status_code, 400)
            approval.refresh_from_db()
            self.assertEqual((approval.status, approval.amount), (status, Decimal("200")))
        self.assertEqual(Notification.objects.count(), 0)

    def test_pending_edits_notify_reviewer_but_noop_does_not_duplicate(self):
        approval = self.approval()
        self.as_user(self.requester)
        url = f"/api/approval-requests/{approval.pk}/"
        self.assertEqual(self.client.patch(url, {"note": "Synthetic update"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"note": "Synthetic update"}, format="json").status_code, 200)
        self.assertEqual(Notification.objects.get().kind, "approval_updated")
        self.assertEqual(Notification.objects.get().recipient_id, self.manager.pk)

    def test_unprivileged_review_and_cross_company_review_are_rejected(self):
        approval = self.approval()
        self.as_user(self.requester)
        self.assertEqual(self.client.post(f"/api/approval-requests/{approval.pk}/approve/").status_code, 403)
        self.as_user(self.manager, self.other)
        self.assertEqual(self.client.post(f"/api/approval-requests/{approval.pk}/approve/").status_code, 404)
        self.assertEqual(Notification.objects.count(), 0)

    def test_linked_quote_must_match_company_and_have_snapshot(self):
        approval = self.approval()
        quotation = self.quotation(approval)
        PriceInquiry.objects.filter(pk=quotation.inquiry_id).update(company=self.other)
        url = f"/api/approval-requests/{approval.pk}/approve/"
        self.assertEqual(self.client.post(url).status_code, 400)
        PriceInquiry.objects.filter(pk=quotation.inquiry_id).update(company=self.company)
        Quotation.objects.filter(pk=quotation.pk).update(pending_snapshot=None)
        self.assertEqual(self.client.post(url).status_code, 400)
        approval.refresh_from_db()
        self.assertEqual(approval.status, "pending")
        self.assertEqual(Notification.objects.count(), 0)

    def test_submit_quote_is_atomic_and_blocks_duplicate_pending_proposals(self):
        quotation = self.quotation()
        self.as_user(self.requester)
        url = f"/api/quotations/{quotation.pk}/submit-for-approval/"
        data = {"lines": [{"item_name": "Synthetic submitted", "quantity": "1", "price": "200"}], "note": "Synthetic new note"}
        with patch("crm.models.Quotation.save", side_effect=RuntimeError("Synthetic link failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(url, data, format="json")
        self.assertEqual(ApprovalRequest.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(self.client.post(url, data, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, data, format="json").status_code, 400)
        self.assertEqual(ApprovalRequest.objects.count(), 1)
        self.assertEqual(Notification.objects.get().kind, "approval_submitted")

    def test_pending_quote_and_its_request_cannot_be_edited_separately(self):
        approval = self.approval()
        quotation = self.quotation(approval)
        self.as_user(self.requester)
        self.assertEqual(self.client.patch(f"/api/quotations/{quotation.pk}/", {"note": "Synthetic overwrite"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/approval-requests/{approval.pk}/", {"amount": "999"}, format="json").status_code, 400)
        quotation.refresh_from_db()
        self.assertEqual(quotation.note, "Synthetic previous note")

    def test_client_cannot_attach_arbitrary_approval_to_a_quote(self):
        quotation = self.quotation()
        approval = self.approval()
        self.as_user(self.requester)
        response = self.client.patch(f"/api/quotations/{quotation.pk}/", {"pending_approval": approval.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        quotation.refresh_from_db()
        self.assertIsNone(quotation.pending_approval_id)

    def test_detail_targets_exact_request_and_rechecks_role_and_membership(self):
        self.as_user(self.requester)
        response = self.client.post("/api/approval-requests/", {"request_type": "proposal", "title": "Synthetic sensitive request", "note": "Synthetic PRIVATE", "amount": "12345"}, format="json")
        approval_id = response.data["id"]
        item = Notification.objects.get()
        self.as_user(self.manager)
        response = self.client.get(f"/api/notifications/{item.pk}/")
        self.assertEqual(response.data["detail"]["destination"], f"/approvals?request={approval_id}")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("PRIVATE", self.client.get("/api/notifications/").content.decode())
        self.manager.profile.companies.add(self.company)
        self.manager.is_staff = False
        self.manager.save()
        self.assertEqual(self.client.get(f"/api/notifications/{item.pk}/").status_code, 404)

    @override_settings(CAVI_NOTIFICATIONS_ENABLED=False)
    def test_when_notifications_disabled_approval_still_commits_without_inbox(self):
        approval = self.approval()
        self.quotation(approval)
        self.assertEqual(self.client.post(f"/api/approval-requests/{approval.pk}/approve/").status_code, 200)
        self.assertEqual(Notification.objects.count(), 0)
