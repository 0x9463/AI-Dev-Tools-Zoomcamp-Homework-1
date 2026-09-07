from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account, HouseholdMember, Task
from .services import create_account, create_household, create_task


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MyTasksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def account(name, role=Account.Role.MEMBER):
            return create_account(email=f"{name}@example.com", password="Bright-otter-travels-972!", role=role)

        cls.admin = account("admin", Account.Role.ADMINISTRATOR)
        cls.other_admin = account("other-admin", Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.other_household = create_household(user=cls.other_admin, name="Birch House")
        cls.member = account("member")
        cls.peer = account("peer")
        cls.empty_member = account("empty")
        cls.outsider = account("outsider")
        for user in [cls.member, cls.peer, cls.empty_member]:
            HouseholdMember.objects.create(user=user, household=cls.household)
        cls.mine = create_task(household=cls.household, user=cls.admin, title="Wash dishes", assigned_user=cls.member)
        cls.theirs = create_task(household=cls.household, user=cls.admin, title="Sweep floor", assigned_user=cls.peer)
        # Historical assignments can remain in a former household after membership ends.
        HouseholdMember.objects.create(user=cls.member, household=cls.other_household, active=False)
        cls.former = Task.objects.create(household=cls.other_household, title="Former household task", assigned_user=cls.member)
        cls.url = reverse("my_tasks", args=[cls.household.pk])

    def test_my_assignments_detail_links_and_navigation(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertContains(response, "My Tasks")
        self.assertContains(response, self.mine.title)
        self.assertNotContains(response, self.theirs.title)
        self.assertNotContains(response, self.former.title)
        detail_url = reverse("task_detail", args=[self.household.pk, self.mine.pk])
        self.assertContains(response, f'href="{detail_url}"')
        self.assertContains(self.client.get(detail_url), self.mine.title)
        list_url = reverse("task_list", args=[self.household.pk])
        self.assertContains(response, f'href="{list_url}"')
        household_list = self.client.get(list_url)
        self.assertContains(household_list, self.mine.title)
        self.assertContains(household_list, self.theirs.title)
        self.assertContains(household_list, f'href="{self.url}"')
        self.assertContains(self.client.get(reverse("household_home", args=[self.household.pk])), f'href="{self.url}"')

    def test_submitted_ids_and_filters_cannot_change_scope(self):
        self.client.force_login(self.member)
        forged = {"user": self.peer.pk, "user_id": self.peer.pk, "assigned_user": self.peer.pk,
                  "household": self.other_household.pk, "household_id": self.other_household.pk,
                  "status": "nonexistent"}
        response = self.client.get(self.url, forged)
        self.assertContains(response, self.mine.title)
        self.assertNotContains(response, self.theirs.title)
        self.assertNotContains(response, self.former.title)
        response = self.client.post(self.url, forged)
        self.assertEqual(response.status_code, 405)
        self.assertNotContains(response, self.theirs.title, status_code=405)
        self.assertEqual(Task.objects.count(), 3)
        self.client.force_login(self.peer)
        response = self.client.get(self.url, {"user": self.member.pk})
        self.assertContains(response, self.theirs.title)
        self.assertNotContains(response, self.mine.title)

    def test_empty_state(self):
        self.client.force_login(self.empty_member)
        response = self.client.get(self.url)
        self.assertContains(response, "You have no assigned tasks in this household.")
        self.assertNotContains(response, self.mine.title)
        self.assertNotContains(response, self.theirs.title)

    def test_signed_out_nonmember_and_revoked_membership_cannot_read(self):
        for user, expected in [(None, 302), (self.outsider, 404), (self.other_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            response = self.client.get(self.url, {"user": self.member.pk})
            self.assertEqual(response.status_code, expected)
            self.assertNotContains(response, self.mine.title, status_code=expected)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("my_tasks", args=[self.other_household.pk])).status_code, 404)
        HouseholdMember.objects.filter(user=self.member, household=self.household).update(active=False)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.mine.title, status_code=404)
        self.assertTrue(Task.objects.filter(pk=self.mine.pk).exists())

    def test_inactive_account_cannot_read(self):
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.mine.title, status_code=302)
