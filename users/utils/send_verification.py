from django.conf import settings
from django.urls import reverse

from users.utils.email_service import send_email
from users.utils.verification import generate_verification_token


def send_verification(user):
    token = generate_verification_token(user)

    path = reverse("verify_email")

    verification_link = (
        f"{settings.FRONTEND_URL}{path}"
        f"?user_id={user.id}&token={token}"
    )

    subject = "Подтверждение email — Splitra"

    text_content = (
        "Подтвердите email:\n"
        f"{verification_link}\n\n"
        "Если это не вы — проигнорируйте письмо."
    )

    from django.template.loader import render_to_string

    html_content = render_to_string(
        "emails/verify_email.html",
        {
            "verification_link": verification_link
        }
    )

    send_email(subject, user.email, text_content, html_content)