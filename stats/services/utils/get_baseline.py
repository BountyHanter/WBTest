import zoneinfo
from datetime import datetime, date

from django.conf import settings

from stats.models import CampaignDailyStat, Test


def get_current_baseline_point(test: Test) -> tuple[int, int, date] | None:
    """
    Возвращает текущую baseline-точку для теста:
    (views, clicks, date)
    """

    tz = zoneinfo.ZoneInfo(settings.WB_TIMEZONE)
    today = datetime.now(tz).date()

    today_stat = (
        CampaignDailyStat.objects
        .filter(test=test, date=today)
        .first()
    )

    if today_stat:
        return today_stat.views, today_stat.clicks, today_stat.date

    return None