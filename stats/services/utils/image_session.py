from django.db import IntegrityError
from django.utils import timezone

from stats.models import ImageShowStat, Image
import logging

logger = logging.getLogger(__name__)


def open_image_session(image: Image):
    now = timezone.now()

    # --- защита: baseline должен быть
    if image.baseline_views is None or image.baseline_clicks is None:
        raise ValueError(f"Baseline не установлен | image_id={image.id}")

    open_sessions = list(ImageShowStat.objects.filter(
        image=image,
        finished_at__isnull=True
    ))

    # --- штатный случай: есть одна открытая сессия
    if len(open_sessions) == 1:
        return

    # --- аномалия: больше одной открытой сессии, закрываем все
    if len(open_sessions) > 1:
        logger.warning(
            "Найдено несколько открытых сессий (%s), закрываем все | test_id=%s image_id=%s",
            len(open_sessions),
            image.test.id,
            image.id,
        )

        for session in open_sessions:
            session.finished_at = now
            session.end_views = image.baseline_views
            session.end_clicks = image.baseline_clicks
            session.save(update_fields=["finished_at", "end_views", "end_clicks"])

    # --- создаём новую (с защитой от гонок)
    try:
        ImageShowStat.objects.create(
            test=image.test,
            image=image,
            cycle_number=image.test.current_cycle,

            start_views=image.baseline_views,
            start_clicks=image.baseline_clicks,
            started_at=image.started_at,

            end_views=None,
            end_clicks=None,
            finished_at=None,
        )
    except IntegrityError:
        logger.warning(
            "Race condition при создании сессии | test_id=%s image_id=%s",
            image.test.id,
            image.id,
        )

def close_image_session(image: Image, delta_views: int, delta_clicks: int):
    sessions_qs = ImageShowStat.objects.filter(
        image=image,
        finished_at__isnull=True
    )

    sessions = list(sessions_qs)  # избегаем лишнего count()

    now = timezone.now()

    end_views = image.baseline_views + delta_views
    end_clicks = image.baseline_clicks + delta_clicks

    # --- если есть открытые сессии
    if sessions:
        if len(sessions) > 1:
            logger.warning(
                "Найдено несколько открытых сессий (%s), закрываем все | test_id=%s image_id=%s",
                len(sessions),
                image.test.id,
                image.id,
            )

        for session in sessions:
            session.end_views = end_views
            session.end_clicks = end_clicks
            session.finished_at = now

            session.save(update_fields=[
                "end_views",
                "end_clicks",
                "finished_at",
            ])

    # --- fallback
    else:
        logger.warning(
            "Не найдена открытая сессия, создаём fallback | test_id=%s image_id=%s",
            image.test.id,
            image.id,
        )

        ImageShowStat.objects.create(
            test=image.test,
            image=image,
            cycle_number=image.test.current_cycle,

            start_views=image.baseline_views,
            start_clicks=image.baseline_clicks,
            started_at=image.started_at,

            end_views=end_views,
            end_clicks=end_clicks,
            finished_at=now,
        )
