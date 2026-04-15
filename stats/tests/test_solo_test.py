from datetime import datetime, timedelta
import zoneinfo

import pytest
from django.conf import settings
from django.utils import timezone

from stats.models import CampaignDailyStat, Test
from stats.models import Test as TestModel
from stats.services.tests_manager import TestEngine as Engine, TestEngine
from stats.services.utils.set_baseline import set_baseline_point
from stats.tests.utils.factories import create_user, create_test, create_image, create_wb_token


def _make_sync_stats_mock(step_views: int = 12, step_clicks: int = 3):
    state = {"views": 0, "clicks": 0}
    tz = zoneinfo.ZoneInfo(settings.WB_TIMEZONE)

    def _sync(test: TestModel) -> bool:
        today = datetime.now(tz).date()
        state["views"] += step_views
        state["clicks"] += step_clicks
        CampaignDailyStat.objects.update_or_create(
            test=test,
            date=today,
            defaults={
                "views": state["views"],
                "clicks": state["clicks"],
            },
        )
        return True

    return _sync, state


@pytest.mark.django_db
def test_engine_multi_image_flow_finishes(monkeypatch):
    user = create_user(101)
    wb_token = create_wb_token(user=user)
    test = create_test(
        user=user,
        name="solo_flow",
        wb_token=wb_token,
        impressions_per_cycle=10,
        max_impressions_per_image=30,
        time_per_cycle=3600,
    )

    create_image(test, 1)
    create_image(test, 2)
    create_image(test, 3)

    test.status = test.Status.ACTIVE
    test.started_at = timezone.now()
    test.save(update_fields=["status", "started_at"])

    sync_mock, _ = _make_sync_stats_mock(step_views=12, step_clicks=2)
    monkeypatch.setattr("stats.services.tests_manager.sync_campaign_daily_stats", sync_mock)

    sent_images = []

    def _fake_send(self, image):
        sent_images.append(image.position)

    monkeypatch.setattr(Engine, "_send_image", _fake_send)

    max_ticks = 20
    for _ in range(max_ticks):
        Engine(test=TestModel.objects.get(pk=test.pk)).process()
        test.refresh_from_db()
        if test.status == test.Status.FINISHED:
            break

    assert test.status == test.Status.FINISHED
    assert sent_images
    assert test.current_image is None

    images = list(test.images.order_by("position"))
    assert all(img.total_views >= 0 for img in images)
    assert any(img.status == img.Status.DONE for img in images)


@pytest.mark.django_db
def test_engine_pause_then_resume(monkeypatch):
    user = create_user(102)
    wb_token = create_wb_token(user=user)
    test = create_test(
        user=user,
        name="pause_resume",
        wb_token=wb_token,
        impressions_per_cycle=10,
        max_impressions_per_image=100,
        time_per_cycle=3600,
    )
    create_image(test, 1)
    create_image(test, 2)

    test.status = test.Status.ACTIVE
    test.started_at = timezone.now()
    test.save(update_fields=["status", "started_at"])

    sync_mock, state = _make_sync_stats_mock(step_views=10, step_clicks=1)
    monkeypatch.setattr("stats.services.tests_manager.sync_campaign_daily_stats", sync_mock)
    monkeypatch.setattr(Engine, "_send_image", lambda self, image: None)

    # Первый тик запускает показ первой картинки
    Engine(test=TestModel.objects.get(pk=test.pk)).process()
    test.refresh_from_db()
    current_image_id_before_pause = test.current_image_id
    views_before_pause = state["views"]
    assert current_image_id_before_pause is not None

    # На паузе process должен сразу выйти и не тянуть статистику
    test.status = test.Status.PAUSED
    test.save(update_fields=["status"])
    Engine(test=TestModel.objects.get(pk=test.pk)).process()
    test.refresh_from_db()
    assert test.current_image_id == current_image_id_before_pause
    assert state["views"] == views_before_pause

    # После resume процесс продолжается
    test.status = test.Status.ACTIVE
    test.save(update_fields=["status"])
    TestEngine(test=Test.objects.get(pk=test.pk)).process()
    test.refresh_from_db()
    assert state["views"] > views_before_pause


@pytest.mark.django_db
def test_engine_finishes_when_only_one_eligible_image_remains(monkeypatch):
    user = create_user(103)
    wb_token = create_wb_token(user=user)
    test = create_test(
        user=user,
        name="one_left_finish",
        wb_token=wb_token,
        impressions_per_cycle=10,
        max_impressions_per_image=100,
        time_per_cycle=1,
    )

    img1 = create_image(test, 1)
    img2 = create_image(test, 2)
    img3 = create_image(test, 3)

    # Две картинки считаем уже выбывшими, третья остаётся единственной для current_image
    img1.total_views = test.max_impressions_per_image
    img1.status = img1.Status.DONE
    img1.save(update_fields=["total_views", "status"])

    img2.total_views = test.max_impressions_per_image
    img2.status = img2.Status.DONE
    img2.save(update_fields=["total_views", "status"])

    test.status = test.Status.ACTIVE
    test.current_image = img3
    test.started_at = timezone.now()
    test.save(update_fields=["status", "current_image", "started_at"])

    sync_mock, _ = _make_sync_stats_mock(step_views=12, step_clicks=1)
    monkeypatch.setattr("stats.services.tests_manager.sync_campaign_daily_stats", sync_mock)

    sent_images = []
    monkeypatch.setattr(Engine, "_send_image", lambda self, image: sent_images.append(image.id))

    # Ставим baseline до тика, потом искусственно сдвигаем started_at назад для завершения цикла
    assert sync_mock(test) is True
    assert set_baseline_point(img3) is True
    img3.refresh_from_db()
    img3.started_at = timezone.now() - timedelta(seconds=120)
    img3.save(update_fields=["started_at"])

    Engine(test=TestModel.objects.get(pk=test.pk)).process()
    test.refresh_from_db()
    img3.refresh_from_db()

    assert test.status == test.Status.FINISHED
    assert test.current_image is None
    assert img3.total_views > 0
    assert not sent_images
