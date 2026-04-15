from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import random
import time
import zoneinfo

import httpx
import pytest
from django.conf import settings
from django.db import close_old_connections, connections
from django.utils import timezone

from stats.models import CampaignDailyStat
from stats.models import Test as DBTest
from stats.services.tests_manager import TestEngine as Engine
from stats.tests.utils.factories import create_image, create_test, create_user, create_wb_token


MOCK_API_URL = "http://127.0.0.1:8111/"


def _sync_stats_from_mock_service(test: DBTest) -> bool:
    tz = zoneinfo.ZoneInfo(settings.WB_TIMEZONE)
    today = datetime.now(tz).date()

    token_key = f"{test.wb_token.token}:{test.campaign_id}"

    try:
        response = httpx.get(MOCK_API_URL, params={"wb_token": token_key}, timeout=2.0)
        response.raise_for_status()
        payload = response.json()
        views = int(payload.get("views", 0))
        clicks = int(payload.get("clicks", 0))
    except Exception:
        return False

    CampaignDailyStat.objects.update_or_create(
        test=test,
        date=today,
        defaults={
            "views": views,
            "clicks": clicks,
        },
    )
    return True


def _process_single_test(test_id: int):
    close_old_connections()
    try:
        test = DBTest.objects.get(pk=test_id)
        Engine(test=test).process()
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_stress_300_tests_batched_100_with_mock_service(monkeypatch):
    try:
        health = httpx.get(MOCK_API_URL, params={"wb_token": "__health__"}, timeout=1.0)
        health.raise_for_status()
    except Exception:
        pytest.skip("Mock API at :8111 is unavailable")

    monkeypatch.setattr(
        "stats.services.tests_manager.sync_campaign_daily_stats",
        _sync_stats_from_mock_service,
    )
    monkeypatch.setattr(Engine, "_send_image", lambda self, image: None)

    random.seed(42)
    user = create_user(500)

    tests = []
    total_tests = 300
    for i in range(total_tests):
        wb_token = create_wb_token(user=user, token=f"stress_token_{i}")
        test = create_test(
            user=user,
            name=f"stress_test_{i}",
            wb_token=wb_token,
            impressions_per_cycle=5,
            max_impressions_per_image=20,
            time_per_cycle=2,
        )
        for pos in range(1, 4):
            create_image(test, pos)

        test.status = test.Status.ACTIVE
        test.started_at = timezone.now()
        test.save(update_fields=["status", "started_at"])
        tests.append(test.id)

    batch_size = 100
    max_workers = 20
    max_ticks = 40

    for _ in range(max_ticks):
        active_ids = list(
            DBTest.objects.filter(id__in=tests, status=DBTest.Status.ACTIVE).values_list("id", flat=True)
        )
        if not active_ids:
            break

        for start in range(0, len(active_ids), batch_size):
            batch_ids = active_ids[start:start + batch_size]
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_single_test, test_id) for test_id in batch_ids]
                for future in as_completed(futures):
                    future.result()

        # мок-сервис обновляет статистику раз в секунду, даём накопиться дельте
        time.sleep(1.1)

    unfinished = list(
        DBTest.objects.filter(id__in=tests).exclude(status=DBTest.Status.FINISHED).values_list("id", flat=True)
    )
    assert not unfinished, f"Some tests did not finish: count={len(unfinished)}"

    for test in DBTest.objects.filter(id__in=tests):
        for img in test.images.all():
            assert img.total_views >= 0
            assert img.total_clicks >= 0

    connections.close_all()
