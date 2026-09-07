from smtplib import SMTPException
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .decorators import product_account_required
from .forms import HouseholdForm, InvitationForm, SignupForm, TaskForm
from .models import Account, CompletionSubmission, Household, Invitation, Task
from .services import accept_invitation, approve_submission, can_submit_completion, create_household, create_task, is_administrator, send_invitation, submit_completion


def accessible_households(user):
    return Household.objects.filter(
        Q(admin=user) | Q(memberships__user=user, memberships__active=True)
    ).distinct()


@product_account_required
@require_http_methods(["GET"])
def task_list(request, pk):
    household = get_object_or_404(accessible_households(request.user), pk=pk)
    return render(request, "chores/task_list.html", {
        "household": household, "tasks": household.tasks.select_related("assigned_user"),
        "can_create": household.admin_id == request.user.pk and is_administrator(request.user),
    })


@product_account_required
@require_http_methods(["GET"])
def my_tasks(request, pk):
    household = get_object_or_404(
        Household.objects.filter(memberships__user=request.user, memberships__active=True), pk=pk,
    )
    return render(request, "chores/task_list.html", {
        "household": household,
        "tasks": household.tasks.filter(assigned_user=request.user).select_related("assigned_user"),
        "my_tasks": True,
    })


@product_account_required
@require_http_methods(["GET"])
def task_detail(request, pk, task_pk):
    household = get_object_or_404(accessible_households(request.user), pk=pk)
    task = get_object_or_404(Task.objects.select_related("assigned_user"), household=household, pk=task_pk)
    return render(request, "chores/task_detail.html", {
        "household": household, "task": task,
        "can_submit": task.status == Task.Status.PENDING and can_submit_completion(task, request.user),
    })


@product_account_required
@require_http_methods(["POST"])
def task_submit(request, pk, task_pk):
    household = get_object_or_404(accessible_households(request.user), pk=pk)
    task = get_object_or_404(Task, household=household, pk=task_pk)
    if not can_submit_completion(task, request.user):
        raise PermissionDenied
    try:
        submit_completion(household=household, task_pk=task.pk, user=request.user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Completion submitted for approval.")
    return redirect("task_detail", pk=household.pk, task_pk=task.pk)


@product_account_required
@require_http_methods(["GET", "POST"])
def task_create(request, pk):
    household = get_object_or_404(Household, pk=pk, admin=request.user)
    if not is_administrator(request.user):
        raise PermissionDenied
    form = TaskForm(request.POST if request.method == "POST" else None, household=household)
    if request.method == "POST" and form.is_valid():
        try:
            task = create_task(household=household, user=request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("task_detail", pk=household.pk, task_pk=task.pk)
    return render(request, "chores/task_form.html", {
        "household": household, "form": form,
        "has_assignees": form.fields["assigned_user"].queryset.exists(),
    })


def administrator_household(user, pk):
    if not is_administrator(user):
        raise PermissionDenied
    return get_object_or_404(Household, pk=pk, admin=user)


@product_account_required
@require_http_methods(["GET"])
def pending_approvals(request, pk):
    household = administrator_household(request.user, pk)
    submissions = CompletionSubmission.objects.filter(
        task__household=household, task__status=Task.Status.AWAITING_APPROVAL,
        status=CompletionSubmission.Status.PENDING, reviewed_at__isnull=True, reviewer__isnull=True,
    ).select_related("task", "task__assigned_user", "submitter").order_by("submitted_at", "pk")
    return render(request, "chores/pending_approvals.html", {"household": household, "submissions": submissions})


@product_account_required
@require_http_methods(["POST"])
def submission_approve(request, pk, submission_pk):
    household = administrator_household(request.user, pk)
    submission = get_object_or_404(CompletionSubmission, pk=submission_pk, task__household=household)
    try:
        approve_submission(household=household, submission_pk=submission.pk, user=request.user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Submission approved. Task completed.")
    return redirect("pending_approvals", pk=household.pk)


@product_account_required
def home(request):
    household = Household.objects.filter(
        Q(admin=request.user) | Q(memberships__user=request.user, memberships__active=True)
    ).first()
    if household:
        return redirect("household_home", pk=household.pk)
    return render(request, "chores/home.html", {"can_create": is_administrator(request.user)})


@product_account_required
def household_home(request, pk):
    household = get_object_or_404(
        Household.objects.filter(Q(admin=request.user) | Q(memberships__user=request.user, memberships__active=True)).distinct(),
        pk=pk,
    )
    return render(request, "chores/household.html", {"household": household})


@product_account_required
@require_http_methods(["GET", "POST"])
def household_create(request):
    if not is_administrator(request.user):
        raise PermissionDenied
    form = HouseholdForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            household = create_household(user=request.user, name=form.cleaned_data["name"])
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, "You already have a household.")
        else:
            return redirect("household_home", pk=household.pk)
    return render(request, "chores/form.html", {"form": form, "title": "Create your household", "button": "Create household"})


@product_account_required
@require_http_methods(["GET", "POST"])
def invitation_create(request, pk):
    household = get_object_or_404(Household, pk=pk, admin=request.user)
    if not is_administrator(request.user):
        raise PermissionDenied
    form = InvitationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            send_invitation(household=household, user=request.user, email=form.cleaned_data["email"])
        except (SMTPException, OSError):
            form.add_error(None, "The invitation could not be sent. Please try again.")
        else:
            messages.success(request, "Invitation sent.")
            return redirect("household_home", pk=household.pk)
    return render(request, "chores/form.html", {"form": form, "title": f"Invite a member to {household.name}", "button": "Send invitation"})


@require_http_methods(["GET", "POST"])
def invitation_accept(request, token):
    invitation = get_object_or_404(Invitation.objects.select_related("household"), token=token, accepted_at__isnull=True)
    login_url = reverse("login") + "?" + urlencode({"next": request.path})
    existing = Account.objects.filter(email__iexact=invitation.email).exists()
    needs_login = not request.user.is_authenticated and existing
    form = None if request.user.is_authenticated or needs_login else SignupForm(
        request.POST if request.method == "POST" else None, email=invitation.email
    )
    error = None
    if request.method == "POST" and not needs_login and (form is None or form.is_valid()):
        try:
            user, household = accept_invitation(
                token=token,
                user=request.user if request.user.is_authenticated else None,
                name=form.cleaned_data["name"] if form else "",
                password=form.cleaned_data["password1"] if form else None,
            )
        except ValidationError as exc:
            error = " ".join(exc.messages)
        except IntegrityError:
            error = "The invitation could not be accepted. Sign in if you already have an account."
        else:
            if not request.user.is_authenticated:
                login(request, user, backend="chores.backends.EmailBackend")
            return redirect("household_home", pk=household.pk)
    return render(request, "chores/invitation.html", {
        "invitation": invitation, "form": form, "needs_login": needs_login,
        "login_url": login_url, "error": error,
    })
