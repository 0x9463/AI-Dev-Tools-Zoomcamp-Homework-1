import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account, HouseholdMember, Invitation
from .services import create_account, create_household


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class InvitationAcceptanceTests(TestCase):
    password = "Bright-otter-travels-972!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = create_account(email="admin@example.com", password=cls.password,
                                   role=Account.Role.ADMINISTRATOR)
        cls.other_admin = create_account(email="other@example.com", password=cls.password,
                                         role=Account.Role.ADMINISTRATOR)
        cls.household = create_household(user=cls.admin, name="Maple House")
        cls.other_household = create_household(user=cls.other_admin, name="Birch House")
        cls.member = create_account(email="member@example.com", password=cls.password)

    def invite(self, email="new@example.com"):
        return Invitation.objects.create(household=self.household, inviter=self.admin, email=email)

    def signup(self, **overrides):
        return {"name": "Jamie", "password1": self.password, "password2": self.password,
                **overrides}

    def snapshot(self):
        records = [list(model.objects.order_by("pk").values())
                   for model in [get_user_model(), Account, HouseholdMember, Invitation]]
        # Authentication updates last_login; all identity and credential fields must persist.
        for user in records[0]:
            user.pop("last_login")
        return records

    def test_new_signup_binds_identity_role_and_household_despite_forged_fields(self):
        invitation = self.invite()
        url = reverse("accept_invitation", args=[invitation.token])
        self.assertContains(self.client.get(url), "Create account and join")
        response = self.client.post(url, self.signup(
            email="attacker@example.com", role="administrator", is_staff=True,
            is_superuser=True, household=self.other_household.pk,
            household_id=self.other_household.pk, user_id=self.admin.pk,
        ), follow=True)
        account = Account.objects.get(email=invitation.email)
        user = account.user
        self.assertEqual(account.role, Account.Role.MEMBER)
        self.assertEqual(user.email, invitation.email)
        self.assertEqual(user.first_name, "Jamie")
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        membership = HouseholdMember.objects.get(user=user)
        self.assertEqual(membership.household_id, self.household.pk)
        self.assertTrue(membership.active)
        self.assertIsNotNone(membership.joined_at)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        self.assertContains(response, self.household.name)
        self.assertEqual(self.client.get(reverse("household_home", args=[self.other_household.pk])).status_code, 404)
        self.assertFalse(Account.objects.filter(email="attacker@example.com").exists())

    def test_invalid_signup_preserves_all_records_and_unused_invitation(self):
        invitation = self.invite()
        original = self.snapshot()
        cases = [({}, "This field is required."),
                 (self.signup(name="   "), "This field is required."),
                 (self.signup(password2="different"), "Passwords do not match."),
                 (self.signup(password1="123", password2="123"), "This password is too short."),
                 (self.signup(password1="", password2=""), "This field is required.")]
        for data, error in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("accept_invitation", args=[invitation.token]), data)
                self.assertContains(response, error)
                self.assertEqual(self.snapshot(), original)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_existing_account_authenticates_then_explicitly_accepts_without_identity_changes(self):
        invitation = self.invite("MEMBER@EXAMPLE.COM")
        url = reverse("accept_invitation", args=[invitation.token])
        original = self.snapshot()
        for method in [self.client.get, self.client.post]:
            response = method(url, self.signup())
            self.assertContains(response, "Sign in to accept")
            self.assertEqual(self.snapshot(), original)
        response = self.client.post(reverse("login"), {
            "email": "MeMbEr@Example.com", "password": self.password, "next": url,
        }, follow=True)
        self.assertRedirects(response, url)
        self.assertContains(response, "Accept invitation")
        self.assertEqual(self.snapshot(), original)
        response = self.client.post(url, self.signup(email="different@example.com", role="administrator"), follow=True)
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        self.assertEqual(self.snapshot()[:2], original[:2])
        self.assertEqual(HouseholdMember.objects.get().user_id, self.member.pk)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)

    def test_invalid_and_reused_tokens_create_no_duplicate_records(self):
        invitation = self.invite()
        original = self.snapshot()
        for token in [uuid.uuid4(), "not-a-token"]:
            response = self.client.post(f"/invitations/{token}/", self.signup())
            self.assertEqual(response.status_code, 404)
            self.assertEqual(self.snapshot(), original)
        url = reverse("accept_invitation", args=[invitation.token])
        self.client.post(url, self.signup())
        accepted = self.snapshot()
        for signed_in in [True, False]:
            if not signed_in:
                self.client.logout()
            for method in [self.client.get, self.client.post]:
                response = method(url, self.signup())
                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.snapshot(), accepted)

    def test_ineligible_accounts_cannot_consume_invitation_or_gain_access(self):
        HouseholdMember.objects.create(household=self.other_household, user=self.member)
        wrong_account = create_account(email="wrong@example.com", password=self.password)
        for user, email, error in [
            (self.member, self.member.email, "You already have an active household membership."),
            (self.other_admin, self.other_admin.email, "Administrator accounts cannot join a household as a member."),
            (wrong_account, "new@example.com", "Sign in with the email address this invitation was sent to."),
        ]:
            with self.subTest(user=user.email):
                invitation = self.invite(email)
                original = self.snapshot()
                self.client.force_login(user)
                response = self.client.post(reverse("accept_invitation", args=[invitation.token]), self.signup())
                self.assertContains(response, error)
                self.assertEqual(self.snapshot(), original)
                self.assertEqual(self.client.get(reverse("household_home", args=[self.household.pk])).status_code, 404)

    def test_membership_failure_rolls_back_new_account_and_token_consumption(self):
        invitation = self.invite()
        original = self.snapshot()
        url = reverse("accept_invitation", args=[invitation.token])
        with patch("chores.services.HouseholdMember.objects.create", side_effect=IntegrityError("membership failure")):
            response = self.client.post(url, self.signup())
        self.assertContains(response, "The invitation could not be accepted.")
        self.assertEqual(self.snapshot(), original)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(url, self.signup(), follow=True)
        self.assertRedirects(response, reverse("household_home", args=[self.household.pk]))
        self.assertEqual(HouseholdMember.objects.count(), 1)
