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

    baseline_date = image.date_baseline.date()

    stats = (
        CampaignDailyStat.objects
        .filter(test=image.test, date__gte=baseline_date)
        .order_by("date")
    )

    total_views = 0
    total_clicks = 0
    first_day = True

    for stat in stats:
        if first_day:
            views = stat.views - image.baseline_views
            clicks = stat.clicks - image.baseline_clicks
            first_day = False
        else:
            views = stat.views
            clicks = stat.clicks

        # ❗ ВОТ ЗДЕСЬ ГЛАВНОЕ ИЗМЕНЕНИЕ
        if views < 0 or clicks < 0:
            logger.warning(
                "Отрицательная дельта | image_id=%s stat_date=%s views=%s clicks=%s",
                image.id,
                stat.date,
                views,
                clicks,
            )
            return None

        total_views += views
        total_clicks += clicks

    return total_views, total_clicks