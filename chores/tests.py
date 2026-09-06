import importlib
import uuid
from io import StringIO
from smtplib import SMTPException
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import Account, Household, HouseholdMember, Invitation
from .services import accept_invitation, create_account, create_household, send_invitation


class ProjectSmokeTests(SimpleTestCase):
    def test_admin_login_page_is_available(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PUBLIC_BASE_URL="https://chores.example",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class OnboardingTests(TestCase):
    password = "Bright-otter-travels-972!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = create_account(email="admin@example.com", password=cls.password, role=Account.Role.ADMINISTRATOR)
        cls.other_admin = create_account(email="other@example.com", password=cls.password, role=Account.Role.ADMINISTRATOR)
        cls.member = create_account(email="member@example.com", password=cls.password)
        cls.household = create_household(user=cls.admin, name="Our home")
        cls.other_household = create_household(user=cls.other_admin, name="Other home")

    def invite(self, email="new@example.com", household=None):
        household = household or self.household
        return send_invitation(household=household, user=household.admin, email=email)

    def test_email_login_logout_and_case_insensitivity(self):
        response = self.client.post(reverse("login"), {"email": " ADMIN@EXAMPLE.COM ", "password": self.password})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_invalid_password_inactive_and_username_fallback(self):
        for email, password in [("admin@example.com", "wrong"), ("missing@example.com", self.password), (self.admin.username, self.password)]:
            response = self.client.post(reverse("login"), {"email": email, "password": password})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("_auth_user_id", self.client.session)
        self.admin.is_active = False
        self.admin.save()
        self.client.post(reverse("login"), {"email": self.admin.email, "password": self.password})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_does_not_redirect_to_external_next(self):
        response = self.client.post(reverse("login"), {"email": self.admin.email, "password": self.password, "next": "https://evil.example"})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_protected_pages_require_login(self):
        for url in [reverse("home"), reverse("household_create"), reverse("household_home", args=[self.household.pk]), reverse("create_invitation", args=[self.household.pk])]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse("login") + "?next="))

    def test_provision_command_creates_product_admin_only(self):
        with patch("chores.management.commands.create_administrator.getpass", return_value=self.password):
            call_command("create_administrator", "NEWADMIN@example.com", name="Alex", stdout=StringIO())
        account = Account.objects.get(email="newadmin@example.com")
        self.assertEqual(account.role, Account.Role.ADMINISTRATOR)
        self.assertEqual(account.user.first_name, "Alex")
        self.assertTrue(account.user.check_password(self.password))
        self.assertFalse(account.user.is_staff)
        self.assertFalse(account.user.is_superuser)
        self.assertTrue(account.user.has_usable_password())

    def test_provision_command_rejects_duplicate_mismatch_and_weak_password(self):
        for email, passwords in [(self.admin.email, [self.password, self.password]), ("new@example.com", ["one", "two"]), ("new@example.com", ["123", "123"])]:
            with patch("chores.management.commands.create_administrator.getpass", side_effect=passwords):
                with self.assertRaises(CommandError):
                    call_command("create_administrator", email, stdout=StringIO())
        self.assertFalse(Account.objects.filter(email="new@example.com").exists())

    def test_create_household_and_reject_repeat(self):
        admin = create_account(email="fresh@example.com", password=self.password, role=Account.Role.ADMINISTRATOR)
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("home")), "Create household")
        response = self.client.post(reverse("household_create"), {"name": "Fresh home", "admin": self.other_admin.pk})
        household = Household.objects.get(admin=admin)
        self.assertRedirects(response, reverse("household_home", args=[household.pk]))
        self.client.post(reverse("household_create"), {"name": "Second home"})
        self.assertEqual(Household.objects.filter(admin=admin).count(), 1)

    def test_household_requires_name_and_admin_role(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.post(reverse("household_create"), {"name": "  "}), "This field is required")
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(reverse("household_create"), {"name": "Forbidden"}).status_code, 403)
        self.member.is_staff = self.member.is_superuser = True
        self.member.save()
        self.assertEqual(self.client.get(reverse("household_create")).status_code, 403)

    def test_household_access_is_scoped_to_owner_or_active_member(self):
        url = reverse("household_home", args=[self.household.pk])
        self.client.force_login(self.other_admin)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(url).status_code, 404)
        membership = HouseholdMember.objects.create(household=self.household, user=self.member)
        self.assertContains(self.client.get(url), "Our home")
        self.assertRedirects(self.client.get(reverse("home")), url)
        membership.active = False
        membership.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_send_invitation_and_email_link(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("create_invitation", args=[self.household.pk]), {"email": "NEW@example.com", "household": self.other_household.pk})
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        invitation = Invitation.objects.get()
        self.assertEqual(invitation.email, "new@example.com")
        self.assertEqual(invitation.inviter, self.admin)
        self.assertEqual(invitation.household, self.household)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertIn("Our home", mail.outbox[0].subject)
        self.assertIn("https://chores.example" + reverse("accept_invitation", args=[invitation.token]), mail.outbox[0].body)
        self.assertIsNone(invitation.accepted_at)

    def test_invitation_requires_household_administrator(self):
        HouseholdMember.objects.create(household=self.household, user=self.member)
        for user in [self.other_admin, self.member]:
            self.client.force_login(user)
            response = self.client.post(reverse("create_invitation", args=[self.household.pk]), {"email": "new@example.com"})
            self.assertEqual(response.status_code, 404)
        self.assertFalse(Invitation.objects.exists())

    def test_invalid_email_and_delivery_failure_do_not_create_invitation(self):
        self.client.force_login(self.admin)
        url = reverse("create_invitation", args=[self.household.pk])
        self.assertContains(self.client.post(url, {"email": "bad"}), "Enter a valid email")
        with patch("chores.services.send_mail", side_effect=SMTPException("offline")):
            self.assertContains(self.client.post(url, {"email": "new@example.com"}), "could not be sent")
        self.assertFalse(Invitation.objects.exists())

    def test_invited_signup_joins_and_logs_in(self):
        invitation = self.invite()
        url = reverse("accept_invitation", args=[invitation.token])
        self.assertContains(self.client.get(url), "Create account and join")
        response = self.client.post(url, {"name": "Jamie", "password1": self.password, "password2": self.password, "email": "attacker@example.com", "role": "administrator"})
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        account = Account.objects.get(email="new@example.com")
        self.assertEqual(account.role, Account.Role.MEMBER)
        self.assertFalse(account.user.is_staff)
        self.assertEqual(int(self.client.session["_auth_user_id"]), account.user_id)
        self.assertTrue(account.user.check_password(self.password))
        membership = HouseholdMember.objects.get(user=account.user)
        self.assertTrue(membership.active)
        self.assertIsNotNone(membership.joined_at)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(HouseholdMember.objects.filter(user=account.user).count(), 1)

    def test_invalid_token_and_no_public_signup(self):
        self.assertEqual(self.client.get(reverse("accept_invitation", args=[uuid.uuid4()])).status_code, 404)
        self.assertEqual(self.client.post("/signup/").status_code, 404)

    def test_signup_requires_valid_matching_passwords(self):
        invitation = self.invite()
        url = reverse("accept_invitation", args=[invitation.token])
        for passwords in [("123", "123"), (self.password, "different")]:
            self.assertEqual(self.client.post(url, {"name": "Jamie", "password1": passwords[0], "password2": passwords[1]}).status_code, 200)
        self.assertFalse(Account.objects.filter(email=invitation.email).exists())
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted_at)

    def test_existing_account_must_log_in_before_acceptance(self):
        invitation = self.invite(email=self.member.email)
        url = reverse("accept_invitation", args=[invitation.token])
        self.assertContains(self.client.get(url), "Sign in to accept")
        self.client.post(url, {"name": "Imposter", "password1": self.password, "password2": self.password})
        self.assertFalse(HouseholdMember.objects.filter(user=self.member).exists())
        response = self.client.post(reverse("login"), {"email": self.member.email, "password": self.password, "next": url})
        self.assertRedirects(response, url)
        self.assertFalse(HouseholdMember.objects.filter(user=self.member).exists())
        self.assertRedirects(self.client.post(url), reverse("household_home", args=[self.household.pk]))

    def test_wrong_account_cannot_consume_invitation(self):
        invitation = self.invite()
        self.client.force_login(self.member)
        response = self.client.post(reverse("accept_invitation", args=[invitation.token]))
        self.assertContains(response, "Sign in with the email address")
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted_at)

    def test_second_membership_and_reused_token_are_rejected(self):
        invitation = self.invite(email=self.member.email)
        accept_invitation(token=invitation.token, user=self.member)
        with self.assertRaises(ValidationError):
            accept_invitation(token=invitation.token, user=self.member)
        second = self.invite(email=self.member.email, household=self.other_household)
        with self.assertRaises(ValidationError):
            accept_invitation(token=second.token, user=self.member)
        second.refresh_from_db()
        self.assertIsNone(second.accepted_at)
        self.assertEqual(HouseholdMember.objects.filter(user=self.member, active=True).count(), 1)

    def test_inactive_membership_allows_new_invitation(self):
        HouseholdMember.objects.create(household=self.household, user=self.member, active=False)
        invitation = self.invite(email=self.member.email, household=self.other_household)
        accept_invitation(token=invitation.token, user=self.member)
        self.assertEqual(HouseholdMember.objects.get(user=self.member, active=True).household, self.other_household)

    def test_administrator_cannot_join_another_household(self):
        invitation = self.invite(email=self.other_admin.email)
        with self.assertRaises(ValidationError):
            accept_invitation(token=invitation.token, user=self.other_admin)
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted_at)

    def test_database_constraints_for_identity_membership_and_ownership(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Account.objects.create(user=get_user_model().objects.create(username="duplicate"), email="ADMIN@EXAMPLE.COM")
        HouseholdMember.objects.create(household=self.household, user=self.member)
        with self.assertRaises(IntegrityError), transaction.atomic():
            HouseholdMember.objects.create(household=self.other_household, user=self.member)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Household.objects.create(admin=self.admin, name="Duplicate")

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("login"), {"email": self.admin.email, "password": self.password}).status_code, 403)
        client.force_login(self.admin)
        for url in [reverse("household_create"), reverse("create_invitation", args=[self.household.pk]), reverse("logout")]:
            self.assertEqual(client.post(url).status_code, 403)
        invitation = self.invite()
        self.assertEqual(client.post(reverse("accept_invitation", args=[invitation.token])).status_code, 403)


class ExistingAccountMigrationTests(TestCase):
    def test_existing_users_and_passwords_are_preserved(self):
        user = get_user_model().objects.create_user(username="legacy", email="Legacy@example.com", password="existing-password")
        password_hash = user.password
        migration = importlib.import_module("chores.migrations.0002_existing_accounts")
        migration.import_existing_emails(apps, SimpleNamespace(connection=connection))
        user.refresh_from_db()
        self.assertEqual(user.password, password_hash)
        self.assertEqual(user.username, "legacy")
        self.assertEqual(Account.objects.get(user=user).email, "legacy@example.com")

    def test_duplicate_legacy_emails_fail_without_changing_users(self):
        User = get_user_model()
        User.objects.create_user(username="first", email="same@example.com")
        User.objects.create_user(username="second", email="SAME@example.com")
        migration = importlib.import_module("chores.migrations.0002_existing_accounts")
        with self.assertRaisesMessage(RuntimeError, "duplicate email"):
            migration.import_existing_emails(apps, SimpleNamespace(connection=connection))
        self.assertEqual(User.objects.count(), 2)
        self.assertFalse(Account.objects.exists())

    def test_legacy_user_without_email_is_retained(self):
        user = get_user_model().objects.create_user(username="legacy", password="existing-password")
        migration = importlib.import_module("chores.migrations.0002_existing_accounts")
        migration.import_existing_emails(apps, SimpleNamespace(connection=connection))
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(Account.objects.exists())
