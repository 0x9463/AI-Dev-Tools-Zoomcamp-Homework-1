from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import Account


class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        account = Account.objects.select_related("user").filter(email__iexact=email.strip()).first()
        if account is None:
            get_user_model()().set_password(password)
            return None
        if account.user.check_password(password) and self.user_can_authenticate(account.user):
            return account.user
        return None
