from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Account, CompletionSubmission, HouseholdMember, Task
from .services import approve_submission, create_account, create_household, create_task, edit_task, submit_completion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TaskEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(name, role=Account.Role.MEMBER):
            return create_account(email=f"{name}@example.com", password="Bright-otter-travels-972!", role=role)
        cls.admin = account("admin", Account.Role.ADMINISTRATOR)
        cls.foreign_admin = account("foreign-admin", Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.foreign_household = create_household(user=cls.foreign_admin, name="Birch House")
        cls.member, cls.peer, cls.inactive, cls.foreign = [account(name) for name in ["member", "peer", "inactive", "foreign"]]
        for user, household, active in [(cls.member, cls.household, True), (cls.peer, cls.household, True), (cls.inactive, cls.household, False), (cls.foreign, cls.foreign_household, True)]:
            HouseholdMember.objects.create(user=user, household=household, active=active)
        cls.task = create_task(household=cls.household, user=cls.admin, title="Dishes", description="Blue sponge", assigned_user=cls.member)
        cls.url = reverse("task_edit", args=[cls.household.pk, cls.task.pk])
        cls.detail_url = reverse("task_detail", args=[cls.household.pk, cls.task.pk])

    def edit(self, **overrides):
        values = dict(household=self.household, task_pk=self.task.pk, user=self.admin,
                      title="Clean kitchen", description="", assigned_user=self.peer)
        values.update(overrides)
        return edit_task(**values)

    def test_form_saves_fields_and_audits_old_new_values(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.detail_url), f'href="{self.url}"')
        page = self.client.get(self.url)
        self.assertContains(page, "Dishes")
        self.assertNotContains(page, self.inactive.email)
        self.assertNotContains(page, self.foreign.email)
        response = self.client.post(self.url, {"title": " Clean kitchen ", "description": "", "assigned_user": self.peer.pk,
                                               "status": "completed", "household": self.foreign_household.pk}, follow=True)
        self.assertRedirects(response, self.detail_url)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)
        self.assertEqual(self.task.description, "")
        for page in [response, self.client.get(reverse("task_list", args=[self.household.pk]))]:
            self.assertContains(page, "Clean kitchen")
            self.assertContains(page, self.peer.email)
        event = self.task.history.get(event_type="edited")
        self.assertEqual(event.actor, self.admin)
        self.assertIsNotNone(event.created_at)
        self.assertEqual(event.changes, {
            "title": {"old": "Dishes", "new": "Clean kitchen"},
            "description": {"old": "Blue sponge", "new": ""},
            "assigned_user_id": {"old": self.member.pk, "new": self.peer.pk},
        })
        self.edit(description="Use hot water")
        self.assertContains(self.client.get(self.detail_url), "Use hot water")
        before = self.task.history.count()
        self.edit(description="Use hot water")
        self.assertEqual(self.task.history.count(), before)

    def test_awaiting_and_completed_edits_preserve_workflow_and_reviews(self):
        submission = submit_completion(household=self.household, task_pk=self.task.pk, user=self.member)
        original = CompletionSubmission.objects.values().get(pk=submission.pk)
        self.edit()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.AWAITING_APPROVAL)
        self.assertEqual(CompletionSubmission.objects.values().get(pk=submission.pk), original)
        approve_submission(household=self.household, submission_pk=submission.pk, user=self.admin)
        reviewed = CompletionSubmission.objects.values().get(pk=submission.pk)
        self.edit(title="Kitchen done", assigned_user=self.member)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertEqual(CompletionSubmission.objects.values().get(pk=submission.pk), reviewed)

    def test_reassignment_transfers_submission_actions_and_retains_read_access(self):
        self.edit()
        submit_url = reverse("task_submit", args=[self.household.pk, self.task.pk])
        self.client.force_login(self.member)
        self.assertNotContains(self.client.get(self.detail_url), "Submit completion")
        self.assertContains(self.client.get(reverse("task_list", args=[self.household.pk])), "Clean kitchen")
        self.assertEqual(self.client.post(submit_url).status_code, 403)
        self.client.force_login(self.peer)
        self.assertContains(self.client.get(self.detail_url), "Submit completion")
        self.assertContains(self.client.post(submit_url, follow=True), "Awaiting approval")
        self.assertEqual(self.task.submissions.get().submitter, self.peer)

    def test_invalid_inputs_leave_task_and_history_unchanged(self):
        self.client.force_login(self.admin)
        original = Task.objects.values().get(pk=self.task.pk)
        for title, assignee in [(" \t ", self.peer), ("Changed", self.inactive), ("Changed", self.foreign)]:
            response = self.client.post(self.url, {"title": title, "description": "Changed", "assigned_user": assignee.pk})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            self.assertEqual(Task.objects.values().get(pk=self.task.pk), original)
            self.assertEqual(self.task.history.count(), 1)
        with self.assertRaises(ValidationError):
            self.edit(assigned_user=self.inactive)
        with self.assertRaises(ValidationError):
            self.edit(title=" ")
        self.assertEqual(Task.objects.values().get(pk=self.task.pk), original)

    def test_unauthorized_direct_requests_and_service_calls(self):
        for user, expected in [(None, 302), (self.member, 403), (self.foreign_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for method in [self.client.get, self.client.post]:
                self.assertEqual(method(self.url, {"title": "Forged", "assigned_user": self.peer.pk}).status_code, expected)
        forged = reverse("task_edit", args=[self.foreign_household.pk, self.task.pk])
        self.assertEqual(self.client.post(forged).status_code, 404)
        for user in [self.member, self.foreign_admin]:
            with self.assertRaises(PermissionDenied):
                self.edit(user=user)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Dishes")
        self.assertEqual(self.task.history.count(), 1)

    def test_history_failure_rolls_back_and_post_requires_csrf(self):
        original = Task.objects.values().get(pk=self.task.pk)
        with patch("chores.services.TaskHistory.objects.create", side_effect=IntegrityError("write failed")):
            with self.assertRaises(IntegrityError):
                self.edit()
        self.assertEqual(Task.objects.values().get(pk=self.task.pk), original)
        self.assertEqual(self.task.history.count(), 1)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        self.assertEqual(protected.post(self.url, {"title": "Forged", "assigned_user": self.peer.pk}).status_code, 403)
