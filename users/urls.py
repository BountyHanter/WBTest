from django.urls import path

from users.views.logout import LogoutView
from users.views.register import RegisterView
from users.views.user import MeView
from users.views.verify import VerifyEmailView

urlpatterns = [
    path("logout/", LogoutView.as_view(), name="logout"),

    path("register/", RegisterView.as_view(), name='register'),

    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),

    path("me/", MeView.as_view(), name='me'),
]