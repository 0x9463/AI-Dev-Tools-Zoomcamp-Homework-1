from getpass import getpass

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from chores.models import Account
from chores.services import create_account


class Command(BaseCommand):
    help = "Create a household administrator without Django staff or superuser privileges."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--name", default="")

    def handle(self, *args, **options):
        password = getpass("Password: ")
        if password != getpass("Confirm password: "):
            raise CommandError("Passwords do not match.")
        try:
            create_account(email=options["email"], password=password, name=options["name"], role=Account.Role.ADMINISTRATOR)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        except IntegrityError as error:
            raise CommandError("An account with this email already exists.") from error
        self.stdout.write(self.style.SUCCESS("Household administrator created. Sign in using your email."))
