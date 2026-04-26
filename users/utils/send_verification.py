import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from users.utils.email_service import send_email
from users.utils.verification import generate_verification_token

logger = logging.getLogger(__name__)


def send_verification(user):
    try:
        token = generate_verification_token(user)
        path = reverse("verify_email")
        frontend_url = settings.FRONTEND_URL

        if not frontend_url:
            logger.error(
                "FRONTЕНД_URL не настроен для отправки письма подтверждения",
                extra={"user_id": user.id, "email": user.email},
            )
            raise ValueError("FRONTEND_URL не настроен")

        verification_link = (
            f"{frontend_url}{path}"
            f"?user_id={user.id}&token={token}"
        )

        subject = "Подтверждение email — Splitra"
        text_content = (
            "Подтвердите email:\n"
            f"{verification_link}\n\n"
            "Если это не вы — проигнорируйте письмо."
        )

        html_content = render_to_string(
            "emails/verify_email.html",
            {"verification_link": verification_link},
        )

        send_email(subject, user.email, text_content, html_content)

        logger.info(
            "Письмо для подтверждения email успешно отправлено",
            extra={"user_id": user.id, "email": user.email},
        )

    except Exception:
        logger.exception(
            "Ошибка при отправке письма для подтверждения email",
            extra={
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
        )
        raise