import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from companies.models import Company
from crm.models import Notice, Task
from .models import Notification, PushOutbox
from .service import push_envelope, record_change


@override_settings(CAVI_NOTIFICATIONS_ENABLED=True, ROOT_URLCONF="config.preview_urls")
class NotificationTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name="Synthetic Notify A", code="SYN-NOT-A", business_type="transport")
        self.b = Company.objects.create(name="Synthetic Notify B", code="SYN-NOT-B", business_type="trading")
        users = get_user_model().objects
        self.manager = users.create_user("synthetic-notify-manager", is_staff=True)
        self.member = users.create_user("synthetic-notify-member")
        self.peer = users.create_user("synthetic-notify-peer")
        self.outside = users.create_user("synthetic-notify-outside")
        self.member.profile.companies.add(self.a)
        self.peer.profile.companies.add(self.a)
        self.outside.profile.companies.add(self.b)
        self.client = APIClient()
        self.as_user(self.manager)

    def as_user(self, user, company=None):
        self.client.force_authenticate(user)
        self.client.credentials(HTTP_X_COMPANY_ID=str((company or self.a).pk))

    def create_task(self, assigned=None):
        response = self.client.post("/api/tasks/", {"title": "Synthetic private task", "content": "SYNTHETIC PRIVATE BODY", "assigned_to": (assigned or self.member).pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Task.objects.get(pk=response.data["id"])

    def test_task_api_creates_only_related_recipient_and_unsent_intent(self):
        self.create_task()
        item = Notification.objects.get()
        self.assertEqual(item.recipient_id, self.member.id)
        self.assertEqual(item.company_id, self.a.id)
        self.assertEqual(item.kind, "task_assigned")
        self.assertEqual(PushOutbox.objects.get().state, "not_configured")

    def test_task_and_notice_links_open_exact_records_without_marking_read(self):
        task = self.create_task()
        notice = self.client.post("/api/notices/", {"title": "Synthetic linked notice"}, format="json")
        self.assertEqual(notice.status_code, 201)
        self.as_user(self.member)
        for kind, object_id, route in [("task_assigned", task.pk, "task"), ("notice_published", notice.data["id"], "notice")]:
            item = Notification.objects.get(recipient=self.member, kind=kind, object_id=object_id)
            response = self.client.get(f"/api/notifications/{item.pk}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["detail"]["destination"], f"/records/{route}/{object_id}")
            item.refresh_from_db()
            self.assertIsNone(item.read_at)

    def test_status_change_notifies_creator_and_noop_does_not_duplicate(self):
        task = self.create_task()
        self.as_user(self.member)
        url = f"/api/tasks/{task.pk}/"
        self.assertEqual(self.client.patch(url, {"status": "done"}, format="json").status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.manager, kind="task_updated").exists())
        count = Notification.objects.count()
        self.assertEqual(self.client.patch(url, {"status": "done"}, format="json").status_code, 200)
        self.assertEqual(Notification.objects.count(), count)

    def test_new_notice_api_is_company_scoped_and_does_not_echo_to_author(self):
        response = self.client.post("/api/notices/", {"title": "Synthetic notice", "body": "Synthetic body"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Notice.objects.get(pk=response.data["id"]).company_id, self.a.id)
        self.assertEqual(set(Notification.objects.values_list("recipient_id", flat=True)), {self.member.id, self.peer.id})

    def test_explicit_global_legacy_notice_routes_to_each_current_company(self):
        notice = Notice.objects.create(title="Synthetic global", created_by=self.manager)
        record_change("notice", notice, self.manager)
        self.assertTrue(Notification.objects.filter(recipient=self.outside, company=self.b).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.outside, company=self.a).exists())

    def test_failure_rolls_back_both_business_write_and_notification(self):
        with patch("notifications.service.PushOutbox.objects.get_or_create", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/tasks/", {"title": "Synthetic rollback", "assigned_to": self.member.pk}, format="json")
        self.assertFalse(Task.objects.filter(title="Synthetic rollback").exists())
        self.assertEqual(Notification.objects.count(), 0)

    def test_explicit_event_retry_is_deduplicated(self):
        task = Task.objects.create(company=self.a, title="Synthetic retry", assigned_to=self.member, created_by=self.manager)
        record_change("task", task, self.manager, event_key="synthetic-event-1")
        record_change("task", task, self.manager, event_key="synthetic-event-1")
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(PushOutbox.objects.count(), 1)

    def test_inbox_requires_login_and_never_exposes_other_recipient(self):
        self.create_task()
        item = Notification.objects.get()
        self.as_user(None)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 401)
        self.as_user(self.peer)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)
        self.assertEqual(self.client.get(f"/api/notifications/{item.pk}/").status_code, 404)

    def test_current_membership_and_company_are_rechecked(self):
        self.create_task()
        self.as_user(self.member, self.b)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 403)
        self.member.profile.companies.clear()
        self.as_user(self.member)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 403)

    def test_reassignment_move_and_delete_remove_current_access(self):
        task = self.create_task()
        item = Notification.objects.get()
        self.as_user(self.member)
        self.assertEqual(self.client.get(f"/api/notifications/{item.pk}/").status_code, 200)
        Task.objects.filter(pk=task.pk).update(assigned_to=self.peer)
        self.assertEqual(self.client.get(f"/api/notifications/{item.pk}/").status_code, 404)
        Task.objects.filter(pk=task.pk).update(assigned_to=self.member, company=self.b)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)
        task.delete()
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)

    def test_list_is_private_and_generic_detail_checks_current_resource(self):
        task = self.create_task()
        self.as_user(self.member)
        response = self.client.get("/api/notifications/")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn(task.title, response.content.decode())
        self.assertFalse(response.data["push"]["enabled"])
        item = Notification.objects.get()
        detail = self.client.get(f"/api/notifications/{item.pk}/")
        self.assertEqual(detail.data["detail"]["title"], task.title)
        item.refresh_from_db()
        self.assertIsNone(item.read_at)

    def test_mark_read_only_displayed_owned_ids_and_is_idempotent(self):
        self.create_task()
        item = Notification.objects.get()
        self.create_task(self.peer)
        other = Notification.objects.exclude(pk=item.pk).get()
        self.as_user(self.member)
        response = self.client.post("/api/notifications/read/", {"ids": [item.pk, other.pk]}, format="json")
        self.assertEqual(response.data["updated"], 1)
        other.refresh_from_db()
        self.assertIsNone(other.read_at)
        self.assertEqual(self.client.post("/api/notifications/read/", {"ids": [item.pk]}, format="json").data["updated"], 0)

    def test_pagination_and_input_validation(self):
        task = self.create_task()
        for index in range(52):
            record_change("task", task, self.manager, event_key=f"synthetic-page-{index}")
        self.as_user(self.member)
        first = self.client.get("/api/notifications/").data
        second = self.client.get(f'/api/notifications/?before={first["next_before"]}').data
        self.assertEqual(len(first["results"]), 50)
        self.assertEqual(len(second["results"]), 3)
        self.assertFalse(set(row["id"] for row in first["results"]) & set(row["id"] for row in second["results"]))
        for value in ["-1", "garbage", "9" * 30]:
            self.assertEqual(self.client.get(f"/api/notifications/?before={value}").status_code, 400)
        self.assertEqual(self.client.post("/api/notifications/read/", {"ids": []}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/notifications/read/", {"ids": [1] * 51}, format="json").status_code, 400)

    def test_no_push_private_content_tokens_or_external_routes(self):
        self.create_task()
        payload = push_envelope(Notification.objects.get())
        text = json.dumps(payload)
        self.assertNotIn("PRIVATE", text)
        self.assertNotIn(self.member.username, text)
        self.assertEqual(set(payload["data"]), {"notification_id", "channel"})
        self.assertEqual(payload["data"]["channel"], "preview")

    def test_no_history_backfill_inactive_or_wrong_company_recipient(self):
        self.create_task(self.outside)
        self.assertEqual(Notification.objects.count(), 0)
        self.member.is_active = False
        self.member.save()
        self.create_task()
        self.assertEqual(Notification.objects.count(), 0)

    @override_settings(CAVI_NOTIFICATIONS_ENABLED=False)
    def test_disabled_hooks_do_not_write_notification_tables(self):
        self.create_task()
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 404)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_production_exposes_no_notification_endpoint(self):
        self.assertEqual(self.client.get("/api/notifications/").status_code, 404)
