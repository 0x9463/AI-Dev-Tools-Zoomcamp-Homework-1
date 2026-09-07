from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Account, CompletionSubmission, HouseholdMember, Task, TaskHistory
from .services import create_account, create_household, create_task, submit_completion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CompletionSubmissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(name, role=Account.Role.MEMBER):
            return create_account(email=f"{name}@example.com", password="Bright-otter-travels-972!", role=role)
        cls.admin = account("admin", Account.Role.ADMINISTRATOR)
        cls.foreign_admin = account("foreign-admin", Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.foreign_household = create_household(user=cls.foreign_admin, name="Birch House")
        cls.member = account("member")
        cls.peer = account("peer")
        cls.foreign = account("foreign")
        for user, household in [(cls.member, cls.household), (cls.peer, cls.household), (cls.foreign, cls.foreign_household)]:
            HouseholdMember.objects.create(user=user, household=household)
        cls.task = create_task(household=cls.household, user=cls.admin, title="Dishes", assigned_user=cls.member)
        cls.url = reverse("task_submit", args=[cls.household.pk, cls.task.pk])
        cls.detail_url = reverse("task_detail", args=[cls.household.pk, cls.task.pk])

    def assert_unchanged(self, status=Task.Status.PENDING):
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, status)
        self.assertEqual(CompletionSubmission.objects.count(), 0)
        self.assertEqual(TaskHistory.objects.count(), 1)

    def test_responsible_member_submits_actual_identity_and_time(self):
        self.client.force_login(self.member)
        self.assertContains(self.client.get(self.detail_url), "Submit completion")
        response = self.client.post(self.url, {
            "submitter": self.admin.pk, "task": 99999, "household": self.foreign_household.pk,
            "status": "completed", "points": 100,
        }, follow=True)
        self.assertRedirects(response, self.detail_url)
        self.assertContains(response, "Awaiting approval")
        self.assertNotContains(response, "Submit completion</button>")
        self.assertNotContains(response, "Completed")
        submission = CompletionSubmission.objects.get()
        self.assertEqual(submission.task, self.task)
        self.assertEqual(submission.submitter, self.member)
        self.assertEqual(submission.status, CompletionSubmission.Status.PENDING)
        self.assertIsNotNone(submission.submitted_at)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.AWAITING_APPROVAL)
        event = TaskHistory.objects.get(event_type="completion_submitted")
        self.assertEqual(event.actor, self.member)
        self.assertEqual(event.task, self.task)
        self.assertIsNotNone(event.created_at)

    def test_administrator_submission_still_requires_approval(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Awaiting approval")
        self.assertEqual(CompletionSubmission.objects.get().submitter, self.admin)
        self.assertEqual(TaskHistory.objects.get(event_type="completion_submitted").actor, self.admin)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_user, self.member)

    def test_repeated_submission_has_no_duplicate_or_timestamp_change(self):
        self.client.force_login(self.member)
        self.client.post(self.url)
        self.task.refresh_from_db()
        updated_at = self.task.updated_at
        for user in [self.member, self.admin]:
            self.client.force_login(user)
            self.assertContains(self.client.post(self.url, follow=True), "Only Pending tasks")
        self.task.refresh_from_db()
        self.assertEqual(self.task.updated_at, updated_at)
        self.assertEqual(CompletionSubmission.objects.count(), 1)
        self.assertEqual(TaskHistory.objects.count(), 2)

    def test_ineligible_states_are_refused_without_writes(self):
        self.client.force_login(self.member)
        for status in ["completed", "cancelled", "overdue", "unknown", Task.Status.AWAITING_APPROVAL]:
            Task.objects.filter(pk=self.task.pk).update(status=status)
            self.assertContains(self.client.post(self.url, follow=True), "Only Pending tasks")
            self.assert_unchanged(status)

    def test_unauthorized_requests_and_cross_household_ids(self):
        for user, expected in [(None, 302), (self.peer, 403), (self.foreign, 404), (self.foreign_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.post(self.url, {"submitter": self.member.pk}).status_code, expected)
            self.assert_unchanged()
        self.client.force_login(self.foreign_admin)
        forged = reverse("task_submit", args=[self.foreign_household.pk, self.task.pk])
        self.assertEqual(self.client.post(forged).status_code, 404)
        self.client.force_login(self.member)
        HouseholdMember.objects.filter(user=self.member).update(active=False)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assert_unchanged()

    def test_service_rechecks_permissions_and_rolls_back_claim(self):
        for user in [self.peer, self.foreign_admin]:
            with self.assertRaises(PermissionDenied):
                submit_completion(household=self.household, task_pk=self.task.pk, user=user)
            self.assert_unchanged()
        HouseholdMember.objects.filter(user=self.member).update(active=False)
        with self.assertRaises(PermissionDenied):
            submit_completion(household=self.household, task_pk=self.task.pk, user=self.member)
        self.assert_unchanged()
        with self.assertRaises(ValidationError):
            submit_completion(household=self.foreign_household, task_pk=self.task.pk, user=self.foreign_admin)
        self.assert_unchanged()

    def test_write_failures_roll_back_all_records_and_status(self):
        for target in ["chores.services.CompletionSubmission.objects.create", "chores.services.TaskHistory.objects.create"]:
            with patch(target, side_effect=IntegrityError("write failed")):
                with self.assertRaises(IntegrityError):
                    submit_completion(household=self.household, task_pk=self.task.pk, user=self.member)
            self.assert_unchanged()

    def test_action_requires_post_and_csrf(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.member)
        self.assertEqual(protected.post(self.url).status_code, 403)
        self.assert_unchanged()
