import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Account(models.Model):
    class Role(models.TextChoices):
        ADMINISTRATOR = "administrator", "Administrator"
        MEMBER = "member", "Member"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="account_email_ci_unique")]


class Household(models.Model):
    name = models.CharField(max_length=120)
    admin = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_household"
    )

    def __str__(self):
        return self.name


class HouseholdMember(models.Model):
    household = models.ForeignKey(Household, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    joined_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(active=True), name="one_active_household_per_user"
            ),
        ]


class Invitation(models.Model):
    household = models.ForeignKey(Household, on_delete=models.PROTECT)
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"

    household = models.ForeignKey(Household, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_tasks")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event_type = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
