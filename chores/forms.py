from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import Household


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class EmailLoginForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get("email") and data.get("password"):
            self.user_cache = authenticate(self.request, email=data["email"], password=data["password"])
            if self.user_cache is None:
                raise ValidationError("Enter a valid email address and password.")
        return data

    def get_user(self):
        return self.user_cache


class HouseholdForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name"]


class InvitationForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField()


class SignupForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(max_length=150)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, email, **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        if data.get("password1"):
            user = get_user_model()(email=self.email, first_name=data.get("name", ""))
            try:
                password_validation.validate_password(data["password1"], user)
            except ValidationError as error:
                self.add_error("password1", error)
        return data
