from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Account, HouseholdMember, Task, TaskHistory
from .services import create_account, create_household, create_task


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TaskCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(email, role=Account.Role.MEMBER):
            return create_account(email=email, password="Bright-otter-travels-972!", role=role)
        cls.admin = account("admin@example.com", Account.Role.ADMINISTRATOR)
        cls.other_admin = account("other@example.com", Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.other_household = create_household(user=cls.other_admin, name="Birch House")
        cls.member = account("member@example.com")
        cls.peer = account("peer@example.com")
        cls.inactive = account("inactive@example.com")
        cls.foreign = account("foreign@example.com")
        for user, household, active in [(cls.member, cls.household, True),
                                         (cls.peer, cls.household, True),
                                         (cls.inactive, cls.household, False),
                                         (cls.foreign, cls.other_household, True)]:
            HouseholdMember.objects.create(user=user, household=household, active=active)

    def setUp(self):
        self.url = reverse("task_create", args=[self.household.pk])
        self.list_url = reverse("task_list", args=[self.household.pk])

    def create(self):
        return create_task(household=self.household, user=self.admin,
                           title="Wash dishes", description="Use the blue sponge", assigned_user=self.member)

    def test_creation_records_pending_task_and_history_and_renders_list_detail(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            "title": "  Wash dishes  ", "description": "Use the blue sponge",
            "assigned_user": self.member.pk, "household": self.other_household.pk,
            "status": "completed", "actor": self.other_admin.pk,
        }, follow=True)
        task = Task.objects.get()
        self.assertRedirects(response, reverse("task_detail", args=[self.household.pk, task.pk]))
        self.assertEqual(task.title, "Wash dishes")
        self.assertEqual(task.description, "Use the blue sponge")
        self.assertEqual(task.household_id, self.household.pk)
        self.assertEqual(task.assigned_user_id, self.member.pk)
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
        event = TaskHistory.objects.get()
        self.assertEqual(event.task_id, task.pk)
        self.assertEqual(event.actor_id, self.admin.pk)
        self.assertEqual(event.event_type, "created")
        self.assertIsNotNone(event.created_at)
        for page in [response, self.client.get(self.list_url)]:
            for value in [task.title, self.member.email, "Pending", "Created"]:
                self.assertContains(page, value)
            self.assertTemplateUsed(page, "chores/base.html")
        self.assertContains(response, task.description)
        self.assertContains(self.client.get(self.url), 'class="form-control"')

    def test_optional_description_and_invalid_required_fields(self):
        self.client.force_login(self.admin)
        for data in [{}, {"title": "   ", "assigned_user": self.member.pk}, {"title": "Wash dishes"}]:
            response = self.client.post(self.url, data)
            self.assertContains(response, "This field is required.")
            self.assertFalse(Task.objects.exists())
            self.assertFalse(TaskHistory.objects.exists())
        self.client.post(self.url, {"title": "Wash dishes", "assigned_user": self.member.pk})
        self.assertEqual(Task.objects.get().description, "")

    def test_invalid_assignees_are_not_exposed_or_saved(self):
        self.client.force_login(self.admin)
        page = self.client.get(self.url)
        for user in [self.inactive, self.foreign, self.admin]:
            self.assertNotContains(page, user.email)
            response = self.client.post(self.url, {"title": "Wash dishes", "assigned_user": user.pk})
            self.assertContains(response, "Select a valid choice.")
            self.assertNotContains(response, self.foreign.email)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(TaskHistory.objects.exists())

    def test_all_active_members_read_peer_assignments_but_cannot_create(self):
        task = self.create()
        self.client.force_login(self.peer)
        for url in [self.list_url, reverse("task_detail", args=[self.household.pk, task.pk])]:
            response = self.client.get(url)
            self.assertContains(response, task.title)
            self.assertContains(response, self.member.email)
            self.assertNotContains(response, "Create task")
        for method in [self.client.get, self.client.post]:
            self.assertEqual(method(self.url, {"title": "Forbidden", "assigned_user": self.peer.pk}).status_code, 404)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(TaskHistory.objects.count(), 1)

    def test_outsiders_cannot_read_or_create_and_task_ids_are_household_scoped(self):
        task = self.create()
        for user, status in [(None, 302), (self.other_admin, 404), (self.foreign, 404), (self.inactive, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for url in [self.url, self.list_url, reverse("task_detail", args=[self.household.pk, task.pk])]:
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)
                self.assertNotContains(response, task.title, status_code=status)
            self.assertEqual(self.client.post(self.url, {"title": "Forbidden", "assigned_user": self.member.pk}).status_code, status)
        self.client.force_login(self.other_admin)
        response = self.client.get(reverse("task_detail", args=[self.other_household.pk, task.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(TaskHistory.objects.count(), 1)

    def test_empty_state_and_no_eligible_assignees(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.list_url), "No tasks yet.")
        HouseholdMember.objects.filter(household=self.household).update(active=False)
        response = self.client.get(self.url)
        self.assertContains(response, "No active members are available.")
        self.assertContains(response, 'type="submit" disabled')
        response = self.client.post(self.url, {"title": "Wash dishes", "assigned_user": self.member.pk})
        self.assertContains(response, "Select a valid choice.")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(TaskHistory.objects.exists())

    def test_service_rechecks_permissions_assignment_and_title(self):
        with self.assertRaises(PermissionDenied):
            create_task(household=self.household, user=self.peer, title="Forbidden", assigned_user=self.member)
        with self.assertRaises(ValidationError):
            create_task(household=self.household, user=self.admin, title="   ", assigned_user=self.member)
        with self.assertRaises(ValidationError):
            create_task(household=self.household, user=self.admin, title="Forbidden", assigned_user=self.foreign)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(TaskHistory.objects.exists())

    def test_history_failure_rolls_back_task_and_creation_requires_csrf(self):
        with patch("chores.services.TaskHistory.objects.create", side_effect=IntegrityError("history unavailable")):
            with self.assertRaises(IntegrityError):
                self.create()
        self.assertFalse(Task.objects.exists())
        self.assertFalse(TaskHistory.objects.exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url, {"title": "Wash dishes", "assigned_user": self.member.pk}).status_code, 403)
        self.assertFalse(Task.objects.exists())
