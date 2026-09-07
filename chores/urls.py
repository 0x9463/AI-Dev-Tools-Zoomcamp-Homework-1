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
    path("households/<int:pk>/tasks/", views.task_list, name="task_list"),
    path("households/<int:pk>/tasks/new/", views.task_create, name="task_create"),
    path("households/<int:pk>/tasks/<int:task_pk>/", views.task_detail, name="task_detail"),
    path("households/<int:pk>/invite/", views.invitation_create, name="create_invitation"),
    path("invitations/<uuid:token>/", views.invitation_accept, name="accept_invitation"),
]
