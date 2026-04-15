from django.urls import path

from users.views.login import LoginView
from users.views.register import RegisterView
from users.views.user import MeView

urlpatterns = [
    path("login/", LoginView.as_view(), name='login'),
    path("register/", RegisterView.as_view(), name='register'),
    path("me/", MeView.as_view(), name='me'),
]