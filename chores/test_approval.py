from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Account, CompletionSubmission, HouseholdMember, Task, TaskHistory
from .services import approve_submission, create_account, create_household, create_task, submit_completion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ApprovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(name, role=Account.Role.MEMBER):
            return create_account(email=f"{name}@example.com", password="Bright-otter-travels-972!", role=role)
        cls.admin = account("admin", Account.Role.ADMINISTRATOR)
        cls.foreign_admin = account("foreign-admin", Account.Role.ADMINISTRATOR)
        cls.member = account("member")
        cls.foreign_member = account("foreign-member")
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.foreign_household = create_household(user=cls.foreign_admin, name="Birch House")
        for user, household in [(cls.member, cls.household), (cls.foreign_member, cls.foreign_household)]:
            HouseholdMember.objects.create(user=user, household=household)
        cls.task = create_task(household=cls.household, user=cls.admin, title="Dishes", description="Blue sponge", assigned_user=cls.member)
        cls.foreign_task = create_task(household=cls.foreign_household, user=cls.foreign_admin, title="Foreign secret", assigned_user=cls.foreign_member)
        cls.submission = submit_completion(household=cls.household, task_pk=cls.task.pk, user=cls.member)
        cls.foreign_submission = submit_completion(household=cls.foreign_household, task_pk=cls.foreign_task.pk, user=cls.foreign_member)
        cls.queue_url = reverse("pending_approvals", args=[cls.household.pk])
        cls.approve_url = reverse("submission_approve", args=[cls.household.pk, cls.submission.pk])
        cls.detail_url = reverse("task_detail", args=[cls.household.pk, cls.task.pk])

    def assert_unreviewed(self, task_status=Task.Status.AWAITING_APPROVAL):
        self.task.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(self.task.status, task_status)
        self.assertEqual(self.submission.status, CompletionSubmission.Status.PENDING)
        self.assertIsNone(self.submission.reviewed_at)
        self.assertIsNone(self.submission.reviewer)
        self.assertEqual(self.task.history.count(), 2)

    def test_queue_context_scope_links_and_approval(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.queue_url, {"household": self.foreign_household.pk})
        for value in [self.task.title, self.task.description, self.member.email, f'action="{self.approve_url}"', f'href="{self.detail_url}"']:
            self.assertContains(response, value)
        self.assertNotContains(response, self.foreign_task.title)
        self.assertContains(self.client.get(reverse("household_home", args=[self.household.pk])), f'href="{self.queue_url}"')
        submitted_at = self.submission.submitted_at
        response = self.client.post(self.approve_url, {"reviewer": self.foreign_admin.pk, "submission": self.foreign_submission.pk}, follow=True)
        self.assertRedirects(response, self.queue_url)
        self.assertContains(response, "No submissions awaiting approval.")
        self.assertNotContains(response, self.task.title)
        self.task.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertEqual(self.submission.status, CompletionSubmission.Status.APPROVED)
        self.assertEqual(self.submission.reviewer, self.admin)
        self.assertIsNotNone(self.submission.reviewed_at)
        self.assertEqual(self.submission.submitter, self.member)
        self.assertEqual(self.submission.submitted_at, submitted_at)
        event = self.task.history.get(event_type="completion_approved")
        self.assertEqual(event.actor, self.admin)
        self.assertIsNotNone(event.created_at)
        self.assertContains(self.client.get(self.detail_url), "Completed")
        self.foreign_submission.refresh_from_db()
        self.assertEqual(self.foreign_submission.status, CompletionSubmission.Status.PENDING)

    def test_repeated_or_already_reviewed_submission_has_no_duplicate(self):
        approve_submission(household=self.household, submission_pk=self.submission.pk, user=self.admin)
        self.submission.refresh_from_db()
        reviewed_at = self.submission.reviewed_at
        self.client.force_login(self.admin)
        self.client.post(self.approve_url)
        # Even an inconsistent Awaiting approval task cannot revive an approved review.
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.AWAITING_APPROVAL)
        self.client.post(self.approve_url)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.reviewed_at, reviewed_at)
        self.assertEqual(self.task.history.count(), 3)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.AWAITING_APPROVAL)

    def test_wrong_task_states_do_not_change_review_or_history(self):
        for status in [Task.Status.PENDING, Task.Status.COMPLETED, "cancelled"]:
            Task.objects.filter(pk=self.task.pk).update(status=status)
            with self.assertRaises(ValidationError):
                approve_submission(household=self.household, submission_pk=self.submission.pk, user=self.admin)
            self.assert_unreviewed(status)

    def test_queue_and_action_reject_unauthorized_users_and_ids(self):
        for user, expected in [(None, 302), (self.member, 403), (self.foreign_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            response = self.client.get(self.queue_url)
            self.assertNotContains(response, self.task.title, status_code=expected)
            self.assertEqual(self.client.post(self.approve_url, {"reviewer": self.admin.pk}).status_code, expected)
            self.assert_unreviewed()
        self.client.force_login(self.foreign_admin)
        forged = reverse("submission_approve", args=[self.foreign_household.pk, self.submission.pk])
        self.assertEqual(self.client.post(forged).status_code, 404)
        for user in [self.member, self.foreign_admin]:
            with self.assertRaises(PermissionDenied):
                approve_submission(household=self.household, submission_pk=self.submission.pk, user=user)
        self.assert_unreviewed()

    def test_history_failure_rolls_back_review_and_task(self):
        with patch("chores.services.TaskHistory.objects.create", side_effect=IntegrityError("write failed")):
            with self.assertRaises(IntegrityError):
                approve_submission(household=self.household, submission_pk=self.submission.pk, user=self.admin)
        self.assert_unreviewed()

    def test_post_and_csrf_required(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.approve_url).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        self.assertEqual(protected.post(self.approve_url).status_code, 403)
        self.assert_unreviewed()
