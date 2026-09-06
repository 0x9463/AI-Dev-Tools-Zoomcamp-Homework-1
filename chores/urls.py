from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views
from .forms import EmailLoginForm

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", LoginView.as_view(template_name="registration/login.html", authentication_form=EmailLoginForm), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("households/new/", views.household_create, name="household_create"),
    path("households/<int:pk>/", views.household_home, name="household_home"),
    path("households/<int:pk>/invite/", views.invitation_create, name="create_invitation"),
    path("invitations/<uuid:token>/", views.invitation_accept, name="accept_invitation"),
]
