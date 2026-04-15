from datetime import date, datetime, time

from django.utils import timezone

from stats.models import Image
from stats.services.utils.get_baseline import get_current_baseline_point


def set_baseline_point(image: Image):
    result = get_current_baseline_point(image.test)

    if not result:
        return False

    views, clicks, baseline_point = result

    if isinstance(baseline_point, datetime):
        baseline_dt = baseline_point
    elif isinstance(baseline_point, date):
        baseline_dt = datetime.combine(
            baseline_point,
            time.min,
            tzinfo=timezone.get_current_timezone(),
        )
    else:
        baseline_dt = timezone.now()

    if timezone.is_naive(baseline_dt):
        baseline_dt = timezone.make_aware(baseline_dt, timezone.get_current_timezone())

    image.baseline_views = views
    image.baseline_clicks = clicks
    image.date_baseline = baseline_dt
    image.started_at = timezone.now()

    image.save(update_fields=[
        "baseline_views",
        "baseline_clicks",
        "date_baseline",
        "started_at",
    ])

    return True
