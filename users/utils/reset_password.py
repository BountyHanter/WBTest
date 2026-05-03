import logging

from django.conf import settings
from django.template.loader import render_to_string

from users.utils.email_service import send_email
from users.utils.verification import generate_verification_token

logger = logging.getLogger(__name__)


def send_password_reset(user):
    try:
        token = generate_verification_token(user)
        frontend_url = settings.FRONTEND_URL
        path = "/password-change/"

        if not frontend_url:
            logger.error(
                "FRONTEND_URL не настроен для отправки письма сброса пароля",
                extra={"user_id": user.id, "email": user.email},
            )
            raise ValueError("FRONTEND_URL не настроен")

        reset_link = (
            f"{frontend_url}{path}"
            f"?user_id={user.id}&token={token}"
        )

        subject = "Сброс пароля — Splitra"

        text_content = (
            "Вы запросили сброс пароля.\n"
            f"Ссылка для сброса пароля:\n{reset_link}\n\n"
            "Если это не вы — проигнорируйте письмо."
        )

        html_content = render_to_string(
            "emails/reset_password.html",
            {"verification_link": reset_link},
        )

        send_email(
            subject=subject,
            to=user.email,
            text_content=text_content,
            html_content=html_content,
        )

        logger.info(
            "Письмо для сброса пароля успешно отправлено",
            extra={"user_id": user.id, "email": user.email},
        )

    except Exception:
        logger.exception(
            "Ошибка при отправке письма для сброса пароля",
            extra={
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
        )
        raise