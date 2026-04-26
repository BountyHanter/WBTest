import logging

from django.contrib.auth.tokens import default_token_generator

logger = logging.getLogger(__name__)


def generate_verification_token(user):
    try:
        token = default_token_generator.make_token(user)

        logger.info(
            "Токен подтверждения успешно сгенерирован",
            extra={"user_id": user.id, "email": user.email},
        )

        return token

    except Exception:
        logger.exception(
            "Ошибка при генерации токена подтверждения",
            extra={
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
        )
        raise


def check_verification_token(user, token):
    try:
        is_valid = default_token_generator.check_token(user, token)

        if is_valid:
            logger.info(
                "Токен подтверждения валиден",
                extra={"user_id": user.id, "email": user.email},
            )
        else:
            logger.warning(
                "Токен подтверждения невалиден или истёк",
                extra={"user_id": user.id, "email": user.email},
            )

        return is_valid

    except Exception:
        logger.exception(
            "Ошибка при проверке токена подтверждения",
            extra={
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
        )
        raise