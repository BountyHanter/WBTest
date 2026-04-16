import zoneinfo

from django.conf import settings

from stats.models import CampaignDailyStat, Image
import logging

logger = logging.getLogger(__name__)


def calculate_image_delta(image: Image) -> tuple[int, int] | None:
    """
    Считает просмотры и клики картинки с момента baseline
    по данным CampaignDailyStat.
    """

    if (
        image.baseline_views is None
        or image.baseline_clicks is None
        or image.date_baseline is None
    ):
        return None

    wb_tz = zoneinfo.ZoneInfo(settings.WB_TIMEZONE)
    baseline_date = image.date_baseline.astimezone(wb_tz).date()

    stats = (
        CampaignDailyStat.objects
        .filter(test=image.test, date__gte=baseline_date)
        .order_by("date")
    )

    stats_rows = list(stats)

    logger.info(
        "Расчёт дельты: входные данные | image_id=%s test_id=%s baseline_views=%s baseline_clicks=%s "
        "date_baseline=%s baseline_date=%s stats_dates=%s",
        image.id,
        image.test_id,
        image.baseline_views,
        image.baseline_clicks,
        image.date_baseline,
        baseline_date,
        [str(s.date) for s in stats_rows],
    )

    total_views = 0
    total_clicks = 0
    first_day = True

    for stat in stats_rows:
        if first_day:
            views = stat.views - image.baseline_views
            clicks = stat.clicks - image.baseline_clicks
            first_day = False
        else:
            views = stat.views
            clicks = stat.clicks

        logger.info(
            "Расчёт дельты: шаг | image_id=%s stat_date=%s stat_views=%s stat_clicks=%s "
            "step_views=%s step_clicks=%s total_views_before=%s total_clicks_before=%s",
            image.id,
            stat.date,
            stat.views,
            stat.clicks,
            views,
            clicks,
            total_views,
            total_clicks,
        )

        # ❗ ВОТ ЗДЕСЬ ГЛАВНОЕ ИЗМЕНЕНИЕ
        if views < 0 or clicks < 0:
            logger.warning(
                "Отрицательная дельта | image_id=%s stat_date=%s views=%s clicks=%s "
                "baseline_views=%s baseline_clicks=%s date_baseline=%s baseline_date=%s",
                image.id,
                stat.date,
                views,
                clicks,
                image.baseline_views,
                image.baseline_clicks,
                image.date_baseline,
                baseline_date,
            )
            return None

        total_views += views
        total_clicks += clicks

    logger.info(
        "Расчёт дельты завершён | image_id=%s total_views=%s total_clicks=%s",
        image.id,
        total_views,
        total_clicks,
    )

    return total_views, total_clicks
