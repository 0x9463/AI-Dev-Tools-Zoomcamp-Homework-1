import uuid

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import Account, CompletionSubmission, Household, HouseholdMember, Invitation, Task, TaskHistory


def is_administrator(user):
    return user.is_authenticated and Account.objects.filter(
        user=user, role=Account.Role.ADMINISTRATOR
    ).exists()


def eligible_assignees(household):
    return get_user_model().objects.filter(
        householdmember__household=household, householdmember__active=True,
        is_active=True, account__role=Account.Role.MEMBER,
    ).order_by("email")


@transaction.atomic
def create_task(*, household, user, title, description="", assigned_user):
    if household.admin_id != user.pk or not is_administrator(user):
        raise PermissionDenied
    if not eligible_assignees(household).filter(pk=assigned_user.pk).exists():
        raise ValidationError("Choose an active member of this household.")
    task = Task(household=household, title=title.strip(), description=description,
                assigned_user=assigned_user)
    task.full_clean()
    task.save()
    TaskHistory.objects.create(task=task, actor=user, event_type="created")
    return task


@transaction.atomic
def submit_completion(*, household, task_pk, user):
    # Claim Pending with the first write; SQLite serializes competing submissions.
    claimed = Task.objects.filter(pk=task_pk, household=household, status=Task.Status.PENDING).update(
        status=Task.Status.AWAITING_APPROVAL, updated_at=timezone.now(),
    )
    if not claimed:
        raise ValidationError("Only Pending tasks can be submitted for approval.")
    task = Task.objects.get(pk=task_pk, household=household)
    if not can_submit_completion(task, user):
        raise PermissionDenied
    submission = CompletionSubmission.objects.create(task=task, submitter=user)
    TaskHistory.objects.create(task=task, actor=user, event_type="completion_submitted")
    return submission


def can_submit_completion(task, user):
    if not user.is_authenticated or not user.is_active:
        return False
    if task.household.admin_id == user.pk and is_administrator(user):
        return True
    return task.assigned_user_id == user.pk and eligible_assignees(task.household).filter(pk=user.pk).exists()


@transaction.atomic
def create_account(*, email, password, name="", role=Account.Role.MEMBER):
    email = email.strip().lower()
    validate_email(email)
    if Account.objects.filter(email__iexact=email).exists() or get_user_model().objects.filter(email__iexact=email).exists():
        raise ValidationError("An account with this email already exists. Sign in instead.")
    user = get_user_model()(username=uuid.uuid4().hex, email=email, first_name=name)
    password_validation.validate_password(password, user)
    user.set_password(password)
    user.save()
    Account.objects.create(user=user, email=email, role=role)
    return user


@transaction.atomic
def create_household(*, user, name):
    # Start with a write to serialize competing requests on SQLite.
    if not Account.objects.filter(user=user, role=Account.Role.ADMINISTRATOR).update(role=Account.Role.ADMINISTRATOR):
        raise PermissionDenied
    if Household.objects.filter(admin=user).exists() or HouseholdMember.objects.filter(user=user, active=True).exists():
        raise ValidationError("You already belong to a household.")
    household = Household(name=name.strip(), admin=user)
    household.full_clean()
    household.save()
    return household


@transaction.atomic
def send_invitation(*, household, user, email):
    if household.admin_id != user.pk or not is_administrator(user):
        raise PermissionDenied
    email = email.strip().lower()
    validate_email(email)
    invitation = Invitation.objects.create(household=household, inviter=user, email=email)
    url = settings.PUBLIC_BASE_URL.rstrip("/") + reverse("accept_invitation", args=[invitation.token])
    send_mail(
        f"Invitation to {household.name}",
        f"You have been invited to join {household.name}.\n\nAccept your invitation: {url}\n\n"
        "Use this invitation once to sign up, or sign in with the invited email to accept.",
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )
    return invitation


@transaction.atomic
def accept_invitation(*, token, user=None, name="", password=None):
    # Claim before reading membership state; any failure rolls this back.
    claimed = Invitation.objects.filter(token=token, accepted_at__isnull=True).update(accepted_at=timezone.now())
    if not claimed:
        raise ValidationError("This invitation is invalid or has already been accepted.")
    invitation = Invitation.objects.get(token=token)
    if user is None:
        user = create_account(email=invitation.email, password=password, name=name)
    account = Account.objects.filter(user=user, email__iexact=invitation.email).first()
    if not account or not user.is_active:
        raise ValidationError("Sign in with the email address this invitation was sent to.")
    if account.role != Account.Role.MEMBER or Household.objects.filter(admin=user).exists():
        raise ValidationError("Administrator accounts cannot join a household as a member.")
    if HouseholdMember.objects.filter(user=user, active=True).exists():
        raise ValidationError("You already have an active household membership.")
    HouseholdMember.objects.create(household=invitation.household, user=user)
    return user, invitation.household
