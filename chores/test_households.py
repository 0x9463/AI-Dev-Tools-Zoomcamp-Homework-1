from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account, Household, HouseholdMember
from .services import create_account


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HouseholdCreationTests(TestCase):
    password = "Bright-otter-travels-972!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = create_account(
            email="admin@example.com", password=cls.password,
            role=Account.Role.ADMINISTRATOR,
        )
        cls.other_admin = create_account(
            email="other@example.com", password=cls.password,
            role=Account.Role.ADMINISTRATOR,
        )
        cls.member = create_account(email="member@example.com", password=cls.password)

    def sign_in(self, user):
        response = self.client.post(reverse("login"), {
            "email": user.email, "password": self.password,
        })
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_creation_uses_signed_in_owner_and_displays_saved_name(self):
        self.sign_in(self.admin)
        self.assertContains(self.client.get(reverse("home")), "Create household")
        self.assertContains(self.client.get(reverse("household_create")), 'name="name"')
        response = self.client.post(reverse("household_create"), {
            "name": "  Maple House  ", "admin": self.other_admin.pk,
            "admin_id": self.other_admin.pk,
        }, follow=True)
        household = Household.objects.get()
        self.assertEqual(household.admin_id, self.admin.pk)
        self.assertEqual(household.name, "Maple House")
        self.assertRedirects(response, reverse("household_home", args=[household.pk]))
        self.assertContains(response, "<h1 class=\"h3\">Maple House</h1>", html=True)

    def test_missing_empty_and_whitespace_names_create_nothing(self):
        self.sign_in(self.admin)
        for data in [{}, {"name": ""}, {"name": "   "}, {"name": "\t\r\n"}]:
            with self.subTest(data=data):
                response = self.client.post(reverse("household_create"), data)
                self.assertContains(response, "This field is required.")
                self.assertFormError(response.context["form"], "name", "This field is required.")
                self.assertFalse(Household.objects.exists())

    def test_repeat_creation_preserves_original_after_logout_and_login(self):
        self.sign_in(self.admin)
        self.client.post(reverse("household_create"), {"name": "Original House"})
        original = Household.objects.get()
        original_rows = list(Household.objects.values())
        response = self.client.post(reverse("household_create"), {
            "name": "Replacement House", "id": original.pk, "pk": original.pk,
        })
        self.assertContains(response, "You already belong to a household.")
        self.assertEqual(list(Household.objects.values()), original_rows)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.sign_in(self.admin)
        response = self.client.get(reverse("home"), follow=True)
        self.assertRedirects(response, reverse("household_home", args=[original.pk]))
        self.assertContains(response, "Original House")
        self.assertNotContains(response, "Replacement House")
        self.assertEqual(list(Household.objects.values()), original_rows)

    def test_signed_out_requests_require_login_and_create_nothing(self):
        household = Household.objects.create(admin=self.admin, name="Private House")
        original_rows = list(Household.objects.values())
        for url in [reverse("home"), reverse("household_create"),
                    reverse("household_home", args=[household.pk])]:
            for method in [self.client.get, self.client.post]:
                with self.subTest(url=url, method=method.__name__):
                    response = method(url, {"name": "Unauthorized House"})
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse("login") + "?next="))
                    self.assertNotContains(response, "Private House", status_code=302)
                    self.assertEqual(list(Household.objects.values()), original_rows)

    def test_member_cannot_create_with_or_without_active_membership(self):
        household = Household.objects.create(admin=self.admin, name="Private House")
        original_rows = list(Household.objects.values())
        self.sign_in(self.member)
        for active_membership in [False, True]:
            with self.subTest(active_membership=active_membership):
                if active_membership:
                    HouseholdMember.objects.create(household=household, user=self.member)
                self.assertEqual(self.client.get(reverse("household_create")).status_code, 403)
                response = self.client.post(reverse("household_create"), {
                    "name": "Unauthorized House", "role": "administrator",
                    "admin": self.admin.pk, "household_id": household.pk,
                })
                self.assertEqual(response.status_code, 403)
                self.assertEqual(list(Household.objects.values()), original_rows)

    def test_administrators_cannot_read_or_change_each_others_household(self):
        first = Household.objects.create(admin=self.admin, name="Maple Private House")
        second = Household.objects.create(admin=self.other_admin, name="Birch Private House")
        original_rows = list(Household.objects.order_by("pk").values())
        for user, own, other in [(self.admin, first, second), (self.other_admin, second, first)]:
            with self.subTest(user=user.email):
                self.sign_in(user)
                own_url = reverse("household_home", args=[own.pk])
                other_url = reverse("household_home", args=[other.pk])
                response = self.client.get(reverse("home"), follow=True)
                self.assertRedirects(response, own_url)
                self.assertContains(response, own.name)
                self.assertNotContains(response, other.name)
                identifiers = {"id": other.pk, "pk": other.pk, "household": other.pk,
                               "household_id": other.pk, "admin": other.admin_id,
                               "admin_id": other.admin_id, "name": "Tampered House"}
                for method in [self.client.get, self.client.post]:
                    response = method(other_url, identifiers)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotContains(response, other.name, status_code=404)
                    response = method(own_url, identifiers)
                    self.assertContains(response, own.name)
                    self.assertNotContains(response, other.name)
                response = self.client.get(reverse("home"), identifiers, follow=True)
                self.assertRedirects(response, own_url)
                self.assertNotContains(response, other.name)
                response = self.client.post(reverse("household_create"), identifiers)
                self.assertContains(response, "You already belong to a household.")
                self.assertEqual(list(Household.objects.order_by("pk").values()), original_rows)
