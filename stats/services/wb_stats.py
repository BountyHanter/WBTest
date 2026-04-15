import time
import zoneinfo
from datetime import datetime, timedelta

import httpx
from django.conf import settings

from stats.models import CampaignDailyStat, Test
import logging


logger = logging.getLogger(__name__)


def sync_campaign_daily_stats(test: Test) -> bool:
    """
    Синхронизирует статистику WB (today + yesterday) в CampaignDailyStat.

    Возвращает:
        True  — если успешно
        False — если не удалось получить данные
    """

    url = settings.WB_STATS_URL

    tz = zoneinfo.ZoneInfo(settings.WB_TIMEZONE)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    params = {
        "ids": test.campaign_id,
        "beginDate": yesterday.isoformat(),
        "endDate": today.isoformat(),
    }

    headers = {
        "Authorization": test.wb_token.token,
        "accept": "application/json",
    }

    attempts = 3

    for attempt in range(1, attempts + 1):
        try:
            response = httpx.get(
                url,
                params=params,
                headers=headers,
                timeout=10.0,
            )

            # --- 5xx → ретрай
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Ошибка сервера {response.status_code}",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()
            data = response.json()

            if not data:
                return False

            days = data[0].get("days", [])

            today_stat = None
            yesterday_stat = None

            for day in days:
                day_raw = day.get("date")
                if not day_raw:
                    continue

                try:
                    day_dt = datetime.fromisoformat(day_raw.replace("Z", "+00:00"))
                    day_date = day_dt.astimezone(tz).date()
                except Exception:
                    continue

                day_result = {
                    "date": day_date,
                    "views": int(day.get("views", 0)),
                    "clicks": int(day.get("clicks", 0)),
                }

                if day_date == today:
                    today_stat = day_result
                elif day_date == yesterday:
                    yesterday_stat = day_result

            # --- today обязателен
            if today_stat is None:
                logger.warning(
                    "Нет данных за сегодня | test_id=%s",
                    test.id,
                )
                return False

            # --- записываем today
            CampaignDailyStat.objects.update_or_create(
                test=test,
                date=today_stat["date"],
                defaults={
                    "views": today_stat["views"],
                    "clicks": today_stat["clicks"],
                }
            )

            # --- записываем yesterday (если есть)
            if yesterday_stat:
                CampaignDailyStat.objects.update_or_create(
                    test=test,
                    date=yesterday_stat["date"],
                    defaults={
                        "views": yesterday_stat["views"],
                        "clicks": yesterday_stat["clicks"],
                    }
                )

            logger.info(
                "Статистика WB синхронизирована | test_id=%s | today=%s | yesterday=%s",
                test.id,
                today_stat,
                yesterday_stat,
            )

            return True

        # --- сетевые ошибки → ретрай
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(
                "Ошибка сети WB (попытка %s/%s) | test_id=%s: %s",
                attempt,
                attempts,
                test.id,
                e,
            )

        # --- 5xx → ретрай
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                logger.warning(
                    "Ошибка сервера WB (попытка %s/%s) | test_id=%s: %s",
                    attempt,
                    attempts,
                    test.id,
                    e,
                )
            else:
                logger.exception(
                    "Ошибка клиента WB | test_id=%s: %s",
                    test.id,
                    e,
                )
                return False

        # --- кривой ответ
        except (KeyError, TypeError, ValueError) as e:
            logger.exception(
                "Некорректный ответ WB | test_id=%s: %s",
                test.id,
                e,
            )
            return False

        # --- прочее
        except Exception as e:
            logger.exception(
                "Неожиданная ошибка WB | test_id=%s: %s",
                test.id,
                e,
            )
            return False

        if attempt < attempts:
            time.sleep(5)

    logger.error(
        "Синхронизация WB не удалась после %s попыток | test_id=%s",
        attempts,
        test.id,
    )
    return False
