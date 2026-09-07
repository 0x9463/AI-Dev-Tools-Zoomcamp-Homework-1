from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Account, CompletionSubmission, HouseholdMember, Task
from .services import approve_submission, create_account, create_household, create_task, reject_submission, submit_completion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RejectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(name, role=Account.Role.MEMBER):
            return create_account(email=f"{name}@example.com", password="Bright-otter-travels-972!", role=role)
        cls.admin = account("admin", Account.Role.ADMINISTRATOR)
        cls.foreign_admin = account("foreign", Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.foreign_household = create_household(user=cls.foreign_admin, name="Birch House")
        cls.member = account("member")
        HouseholdMember.objects.create(user=cls.member, household=cls.household)
        cls.task = create_task(household=cls.household, user=cls.admin, title="Dishes", assigned_user=cls.member)
        cls.submission = submit_completion(household=cls.household, task_pk=cls.task.pk, user=cls.member)
        cls.url = reverse("submission_reject", args=[cls.household.pk, cls.submission.pk])
        cls.detail_url = reverse("task_detail", args=[cls.household.pk, cls.task.pk])

    def reject(self, reason="Please wash the pans too."):
        return reject_submission(household=self.household, submission_pk=self.submission.pk, user=self.admin, reason=reason)

    def assert_unreviewed(self, status=Task.Status.AWAITING_APPROVAL):
        self.task.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(self.task.status, status)
        self.assertEqual(self.submission.status, CompletionSubmission.Status.PENDING)
        self.assertIsNone(self.submission.reviewer)
        self.assertIsNone(self.submission.reviewed_at)
        self.assertEqual(self.submission.rejection_reason, "")
        self.assertEqual(self.task.history.count(), 2)

    def test_rejection_resubmission_and_approval_preserve_original_attempt(self):
        self.client.force_login(self.admin)
        queue = self.client.get(reverse("pending_approvals", args=[self.household.pk]))
        self.assertContains(queue, f'action="{self.url}"')
        self.assertContains(queue, "Rejection reason")
        response = self.client.post(self.url, {"reason": "  Wash the pans too.  ", "reviewer": self.foreign_admin.pk}, follow=True)
        self.assertContains(response, "No submissions awaiting approval.")
        self.submission.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)
        self.assertEqual(self.submission.status, CompletionSubmission.Status.REJECTED)
        self.assertEqual(self.submission.reviewer, self.admin)
        self.assertIsNotNone(self.submission.reviewed_at)
        self.assertEqual(self.submission.rejection_reason, "Wash the pans too.")
        event = self.task.history.get(event_type="completion_rejected")
        self.assertEqual(event.actor, self.admin)
        self.assertIsNotNone(event.created_at)
        original = CompletionSubmission.objects.filter(pk=self.submission.pk).values().get()
        self.client.force_login(self.member)
        response = self.client.get(self.detail_url)
        for value in ["Wash the pans too.", self.admin.email, self.member.email, "Submit completion", "Rejected"]:
            self.assertContains(response, value)
        response = self.client.post(reverse("task_submit", args=[self.household.pk, self.task.pk]), follow=True)
        self.assertContains(response, "Awaiting approval")
        self.assertContains(response, "Wash the pans too.")
        fresh = self.task.submissions.exclude(pk=self.submission.pk).get()
        self.assertEqual(fresh.status, CompletionSubmission.Status.PENDING)
        approve_submission(household=self.household, submission_pk=fresh.pk, user=self.admin)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertEqual(CompletionSubmission.objects.filter(pk=self.submission.pk).values().get(), original)
        self.assertEqual(self.task.submissions.count(), 2)

    def test_missing_or_whitespace_reason_has_feedback_and_no_writes(self):
        self.client.force_login(self.admin)
        for data in [{}, {"reason": " \n\t "}]:
            self.assertContains(self.client.post(self.url, data, follow=True), "A written rejection reason is required.")
            self.assert_unreviewed()

    def test_repeated_decisions_do_not_overwrite_prior_review_or_new_attempt(self):
        self.reject()
        original = CompletionSubmission.objects.get(pk=self.submission.pk).__dict__.copy()
        submit_completion(household=self.household, task_pk=self.task.pk, user=self.member)
        with self.assertRaises(ValidationError):
            self.reject("Replace the reason")
        self.assertEqual(CompletionSubmission.objects.get(pk=self.submission.pk).rejection_reason, original["rejection_reason"])
        self.assertEqual(CompletionSubmission.objects.get(pk=self.submission.pk).reviewed_at, original["reviewed_at"])
        self.assertEqual(self.task.history.count(), 4)
        fresh = self.task.submissions.get(status=CompletionSubmission.Status.PENDING)
        approve_submission(household=self.household, submission_pk=fresh.pk, user=self.admin)
        with self.assertRaises(ValidationError):
            reject_submission(household=self.household, submission_pk=fresh.pk, user=self.admin, reason="Too late")
        self.assertEqual(self.task.history.count(), 5)

    def test_ineligible_task_states_refuse_rejection(self):
        for status in [Task.Status.PENDING, Task.Status.COMPLETED, "cancelled"]:
            Task.objects.filter(pk=self.task.pk).update(status=status)
            with self.assertRaises(ValidationError):
                self.reject()
            self.assert_unreviewed(status)

    def test_unauthorized_forged_requests_cannot_change_review(self):
        for user, expected in [(None, 302), (self.member, 403), (self.foreign_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.post(self.url, {"reason": "Forged", "reviewer": self.admin.pk}).status_code, expected)
            self.assert_unreviewed()
        forged = reverse("submission_reject", args=[self.foreign_household.pk, self.submission.pk])
        self.assertEqual(self.client.post(forged, {"reason": "Forged"}).status_code, 404)
        for user in [self.member, self.foreign_admin]:
            with self.assertRaises(PermissionDenied):
                reject_submission(household=self.household, submission_pk=self.submission.pk, user=user, reason="Forged")
        self.assert_unreviewed()

    def test_failure_rolls_back_and_action_requires_post_csrf(self):
        with patch("chores.services.TaskHistory.objects.create", side_effect=IntegrityError("write failed")):
            with self.assertRaises(IntegrityError):
                self.reject()
        self.assert_unreviewed()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        self.assertEqual(protected.post(self.url, {"reason": "No token"}).status_code, 403)
        self.assert_unreviewed()
