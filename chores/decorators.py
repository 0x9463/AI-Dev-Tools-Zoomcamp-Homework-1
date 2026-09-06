from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Account


def product_account_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not Account.objects.filter(user=request.user).exists():
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
