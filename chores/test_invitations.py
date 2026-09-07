from contextlib import redirect_stdout
from io import StringIO
from smtplib import SMTPException
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account, HouseholdMember, Invitation
from .services import create_account, create_household


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PUBLIC_BASE_URL="https://chores.example/",
    DEFAULT_FROM_EMAIL="invites@chores.example",
)
class InvitationSendingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        password = "Bright-otter-travels-972!"
        cls.admin = create_account(email="admin@example.com", password=password,
                                   role=Account.Role.ADMINISTRATOR)
        cls.other_admin = create_account(email="other@example.com", password=password,
                                         role=Account.Role.ADMINISTRATOR)
        cls.member = create_account(email="member@example.com", password=password)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.other_household = create_household(user=cls.other_admin, name="Birch House")
        HouseholdMember.objects.create(household=cls.household, user=cls.member)

    def setUp(self):
        self.url = reverse("create_invitation", args=[self.household.pk])

    def test_form_sends_unique_unaccepted_invitations_using_trusted_fields(self):
        self.client.force_login(self.admin)
        form = self.client.get(self.url)
        self.assertContains(form, 'class="form-control"')
        self.assertContains(form, 'name="email"')
        self.assertFalse(Invitation.objects.exists())
        for address in [" First@Example.com ", "second@example.com"]:
            response = self.client.post(self.url, {
                "email": address, "household": self.other_household.pk,
                "household_id": self.other_household.pk, "inviter": self.other_admin.pk,
                "inviter_id": self.other_admin.pk, "accepted_at": "2026-01-01",
                "token": "00000000-0000-0000-0000-000000000000",
                "PUBLIC_BASE_URL": "https://untrusted.example",
            }, follow=True)
            self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
            self.assertContains(response, "Invitation sent.")
        invitations = list(Invitation.objects.order_by("pk"))
        self.assertEqual(len(invitations), 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotEqual(invitations[0].token, invitations[1].token)
        for invitation, message in zip(invitations, mail.outbox):
            self.assertEqual(invitation.household_id, self.household.pk)
            self.assertEqual(invitation.inviter_id, self.admin.pk)
            self.assertIsNone(invitation.accepted_at)
            self.assertIsNotNone(invitation.created_at)
            self.assertEqual(invitation.token.version, 4)
            self.assertEqual(message.to, [invitation.email])
            self.assertEqual(message.from_email, "invites@chores.example")
            self.assertIn(self.household.name, message.subject)
            self.assertIn(self.household.name, message.body)
            self.assertIn("https://chores.example" + reverse("accept_invitation", args=[invitation.token]),
                          message.body)
            self.assertNotIn("untrusted.example", message.body)
        self.assertEqual([invitation.email for invitation in invitations],
                         ["first@example.com", "second@example.com"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_prints_corresponding_signup_link(self):
        self.client.force_login(self.admin)
        output = StringIO()
        with redirect_stdout(output):
            response = self.client.post(self.url, {"email": "new@example.com"})
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        invitation = Invitation.objects.get()
        self.assertIn("https://chores.example" + reverse("accept_invitation", args=[invitation.token]),
                      output.getvalue())
        self.assertIn("To: new@example.com", output.getvalue())
        self.assertIn("From: invites@chores.example", output.getvalue())

    def test_blank_and_invalid_email_show_errors_without_records_or_messages(self):
        self.client.force_login(self.admin)
        for data, error in [({}, "This field is required."),
                            ({"email": ""}, "This field is required."),
                            ({"email": " \t "}, "This field is required."),
                            ({"email": "invalid"}, "Enter a valid email address."),
                            ({"email": "missing@"}, "Enter a valid email address.")]:
            with self.subTest(data=data):
                response = self.client.post(self.url, data)
                self.assertContains(response, error)
                self.assertFormError(response.context["form"], "email", error)
                self.assertFalse(Invitation.objects.exists())
                self.assertEqual(len(mail.outbox), 0)

    def test_failed_delivery_rolls_back_only_attempt_and_allows_retry(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {"email": "existing@example.com"}, follow=True)
        original = list(Invitation.objects.values())
        for error in [SMTPException("SMTP unavailable"), OSError("Connection failed")]:
            with self.subTest(error=type(error).__name__):
                with patch("chores.services.send_mail", side_effect=error):
                    response = self.client.post(self.url, {"email": "retry@example.com"})
                self.assertContains(response, "The invitation could not be sent. Please try again.")
                self.assertNotContains(response, "Invitation sent.")
                self.assertEqual(list(Invitation.objects.values()), original)
                self.assertEqual(len(mail.outbox), 1)
        response = self.client.post(self.url, {"email": "retry@example.com"}, follow=True)
        self.assertContains(response, "Invitation sent.")
        self.assertEqual(Invitation.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Invitation.objects.filter(email="retry@example.com").count(), 1)

    def test_unauthorized_requests_cannot_send_or_disclose_existing_tokens(self):
        invitation = Invitation.objects.create(household=self.household, inviter=self.admin,
                                               email="private@example.com")
        original = list(Invitation.objects.values())
        forged = {"email": "attacker@example.com", "household": self.household.pk,
                  "household_id": self.household.pk, "inviter": self.admin.pk,
                  "admin": self.admin.pk, "role": "administrator"}
        for user, expected in [(None, 302), (self.member, 404), (self.other_admin, 404)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for method in [self.client.get, self.client.post]:
                with self.subTest(user=user, method=method.__name__):
                    response = method(self.url, forged)
                    self.assertEqual(response.status_code, expected)
                    if user is None:
                        self.assertTrue(response.url.startswith(reverse("login") + "?next="))
                    self.assertNotContains(response, str(invitation.token), status_code=expected)
                    self.assertNotContains(response, invitation.email, status_code=expected)
                    self.assertEqual(list(Invitation.objects.values()), original)
                    self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.other_admin)
        self.client.post(reverse("create_invitation", args=[self.other_household.pk]), forged)
        created = Invitation.objects.exclude(pk=invitation.pk).get()
        self.assertEqual(created.household_id, self.other_household.pk)
        self.assertEqual(created.inviter_id, self.other_admin.pk)
        self.assertNotIn(str(invitation.token), mail.outbox[0].body)
        invitation.refresh_from_db()
        self.assertEqual(list(Invitation.objects.filter(pk=invitation.pk).values()), original)
        self.client.force_login(self.member)
        response = self.client.get(reverse("household_home", args=[self.household.pk]))
        self.assertNotContains(response, str(invitation.token))
        self.assertNotContains(response, invitation.email)
