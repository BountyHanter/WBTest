import logging
import socket

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection


logger = logging.getLogger(__name__)


def send_email(subject, to, text_content, html_content):
    timeout = int(getattr(settings, "EMAIL_TIMEOUT", 10))

    try:
        connection = get_connection(timeout=timeout)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[to],
            connection=connection,
        )
        email.attach_alternative(html_content, "text/html")
        sent_count = email.send()

        if sent_count < 1:
            logger.error(
                "Письмо не отправлено: сервер не принял ни одного получателя",
                extra={"to": to, "subject": subject, "timeout": timeout},
            )
            raise RuntimeError("Письмо не было отправлено")

        logger.info(
            "Письмо успешно отправлено",
            extra={"to": to, "subject": subject, "timeout": timeout},
        )

    except socket.timeout:
        logger.exception(
            "Таймаут SMTP при отправке письма",
            extra={"to": to, "subject": subject, "timeout": timeout},
        )
        raise

    except Exception:
        logger.exception(
            "Непредвиденная ошибка при отправке письма",
            extra={"to": to, "subject": subject, "timeout": timeout},
        )
        raise


if __name__ == "__main__":
    import os
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    from django.template.loader import render_to_string

    verification_link = "http://localhost:8000/test-link"

    html_content = render_to_string(
        "emails/verify_email.html",
        {
            "verification_link": verification_link
        }
    )

    text_content = f"Тестовое письмо:\n{verification_link}"

    send_email(
        subject="Тест Splitra",
        to="gonkong2111@gmail.com",
        text_content=text_content,
        html_content=html_content
    )