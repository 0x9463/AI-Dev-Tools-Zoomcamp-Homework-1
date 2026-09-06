import warnings
from getpass import GetPassWarning
from io import StringIO
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .models import Account, Household, HouseholdMember
from .services import create_account


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EmailAuthenticationTests(TestCase):
    password = "Bright-otter-travels-972!"

    def provision(self, email="ADMIN@example.com", passwords=None):
        output = StringIO()
        with patch("chores.management.commands.create_administrator.getpass",
                   side_effect=passwords or [self.password, self.password]) as prompt:
            call_command("create_administrator", email, name="Alex", stdout=output)
        self.assertEqual(prompt.call_args_list, [call("Password: "), call("Confirm password: ")])
        self.assertNotIn(self.password, output.getvalue())
        return Account.objects.get(email=email.lower()).user

    def test_provisioned_admin_session_layout_logout_and_maintenance_separation(self):
        user = self.provision()
        self.assertEqual(user.account.role, Account.Role.ADMINISTRATOR)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        login_page = self.client.get(reverse("login"))
        self.assertTemplateUsed(login_page, "chores/base.html")
        self.assertContains(login_page, "chores/bootstrap.min.css")
        response = self.client.post(reverse("login"), {
            "email": "AdMiN@EXAMPLE.COM", "password": self.password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create household")
        self.assertTemplateUsed(response, "chores/base.html")
        self.assertContains(response, 'action="/logout/"')
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertRedirects(self.client.get(reverse("admin:index")),
                             reverse("admin:login") + "?next=/admin/")
        response = self.client.post(reverse("admin:login"), {
            "username": user.username, "password": self.password,
        })
        self.assertContains(response, "Please enter the correct username and password for a staff account")
        response = self.client.post(reverse("logout"), follow=True)
        self.assertTemplateUsed(response, "chores/base.html")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.get(reverse("home")), reverse("login") + "?next=/")

    def test_invalid_credentials_show_feedback_without_a_session(self):
        self.provision()
        cases = [
            ({"email": "unknown@example.com", "password": self.password}, "Enter a valid email address and password."),
            ({"email": "admin@example.com", "password": "wrong"}, "Enter a valid email address and password."),
            ({"email": "admin@example.com"}, "This field is required."),
            ({"password": self.password}, "This field is required."),
            ({}, "This field is required."),
        ]
        for data, error in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("login"), data)
                self.assertContains(response, error)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_duplicate_provisioning_preserves_member_admin_and_legacy_users(self):
        member = create_account(email="member@example.com", password=self.password)
        admin = self.provision()
        legacy = get_user_model().objects.create_user(
            username="legacy", email="legacy@example.com", password=self.password, is_staff=True,
        )
        for user in [member, admin, legacy]:
            for email in [user.email, user.email.upper()]:
                with self.subTest(email=email):
                    users_before = list(get_user_model().objects.order_by("pk").values())
                    accounts_before = list(Account.objects.order_by("pk").values())
                    with self.assertRaisesMessage(CommandError, "already exists"):
                        self.provision(email)
                    self.assertEqual(list(get_user_model().objects.order_by("pk").values()), users_before)
                    self.assertEqual(list(Account.objects.order_by("pk").values()), accounts_before)

    def test_invalid_provisioning_creates_neither_user_nor_account(self):
        for email, passwords, error in [
            ("invalid", [self.password] * 2, "Enter a valid email"),
            ("new@example.com", [self.password, "different"], "Passwords do not match"),
            ("new@example.com", ["123"] * 2, "password"),
        ]:
            with self.subTest(email=email, error=error):
                with self.assertRaisesMessage(CommandError, error):
                    self.provision(email, passwords)
                self.assertFalse(get_user_model().objects.exists())
                self.assertFalse(Account.objects.exists())

    def test_password_prompt_refuses_echo_fallback(self):
        def unavailable_terminal(prompt):
            warnings.warn("Can not control echo on the terminal.", GetPassWarning)
            self.fail("Password prompting must stop before the echoing fallback")

        with patch("chores.management.commands.create_administrator.getpass", side_effect=unavailable_terminal):
            with self.assertRaisesMessage(CommandError, "hidden password entry"):
                call_command("create_administrator", "admin@example.com", stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Account.objects.exists())

    def test_legacy_staff_login_retained_but_product_pages_require_account(self):
        legacy = get_user_model().objects.create_user(
            username="maintenance", password=self.password, is_staff=True, is_superuser=True,
        )
        # Even preexisting household links must not bypass the product identity check.
        household = Household.objects.create(name="Protected legacy home", admin=legacy)
        HouseholdMember.objects.create(household=household, user=legacy)
        urls = [reverse("home"), reverse("household_create"),
                reverse("household_home", args=[household.pk]),
                reverse("create_invitation", args=[household.pk])]
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, reverse("login") + "?next=" + url)
            self.assertNotContains(response, household.name, status_code=302)
        self.assertTrue(self.client.login(username=legacy.username, password=self.password))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {"name": "Forbidden"}).status_code, 403)
        self.assertFalse(Account.objects.filter(user=legacy).exists())


class IdentityMigrationTests(TransactionTestCase):
    before = [("chores", "0001_initial")]
    after = [("chores", "0002_existing_accounts")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps
        self.addCleanup(self.restore_migrations)

    def restore_migrations(self):
        # Remove only this test's legacy fixtures before restoring the test schema.
        self.old_apps.get_model("auth", "User").objects.all().delete()
        MigrationExecutor(connection).migrate(self.after)

    def test_real_migration_preserves_identity_and_assigns_only_member_accounts(self):
        User = self.old_apps.get_model("auth", "User")
        for username, email, staff in [("legacy", " Legacy@EXAMPLE.com ", True),
                                       ("regular", "regular@example.com", False),
                                       ("blank", "", True), ("whitespace", "  ", False)]:
            User.objects.create(username=username, email=email, password="existing-encoded-password",
                                is_staff=staff, is_superuser=staff)
        originals = list(User.objects.order_by("pk").values())
        MigrationExecutor(connection).migrate(self.after)
        self.assertEqual(list(get_user_model().objects.order_by("pk").values()), originals)
        self.assertEqual(list(Account.objects.order_by("email").values_list("email", "role")),
                         [("legacy@example.com", "member"), ("regular@example.com", "member")])
        for original in originals:
            self.assertEqual(Account.objects.filter(user_id=original["id"]).exists(),
                             bool(original["email"].strip()))

    def test_duplicate_legacy_email_aborts_real_migration_without_partial_import(self):
        User = self.old_apps.get_model("auth", "User")
        for username, email in [("unique", "unique@example.com"),
                                ("first", "same@example.com"), ("second", " SAME@EXAMPLE.COM ")]:
            User.objects.create(username=username, email=email, password="existing-encoded-password")
        originals = list(User.objects.order_by("pk").values())
        with self.assertRaisesMessage(RuntimeError, "duplicate email"):
            MigrationExecutor(connection).migrate(self.after)
        self.assertEqual(list(User.objects.order_by("pk").values()), originals)
        self.assertFalse(Account.objects.exists())
        self.assertNotIn(("chores", "0002_existing_accounts"),
                         MigrationExecutor(connection).loader.applied_migrations)
