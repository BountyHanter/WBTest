import logging
from pathlib import Path

import httpx
from django.db import transaction
from django.utils import timezone

from django.conf import settings

from stats.services.utils.calculate_delta import calculate_image_delta
from stats.services.utils.ctr import run_ctr
from stats.models import Test, Image
from stats.services.utils.image_session import open_image_session, close_image_session
from stats.services.utils.set_baseline import set_baseline_point
from stats.services.wb_stats import sync_campaign_daily_stats

logger = logging.getLogger(__name__)

class TestEngine:

    def __init__(self, test: Test):
        self.test = test

    def _add_error_safe(self, message: str):
        with transaction.atomic():
            locked_test = (
                Test.objects
                .select_for_update()
                .filter(pk=self.test.pk)
                .first()
            )
            if not locked_test:
                logger.warning(
                    "Не удалось записать ошибку: тест не найден | test_id=%s",
                    self.test.pk,
                )
                return
            locked_test.add_error(message)

    def _send_image(self, image: Image):
        url = settings.WB_UPLOAD_URL

        headers = {
            "Authorization": self.test.wb_token.token,
            "X-Nm-Id": str(self.test.product_id),
            "X-Photo-Number": str(image.position),
        }

        try:
            # открываем файл
            image.image.open("rb")

            ext = Path(image.image.name).suffix.lower()
            mime_by_ext = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }
            content_type = mime_by_ext.get(ext, "application/octet-stream")

            files = {
                "uploadfile": (
                    Path(image.image.name).name,  # только имя файла
                    image.image.file,
                    content_type,
                )
            }

            response = httpx.post(
                url,
                headers=headers,
                files=files,
                timeout=10.0,
            )

            # --- 5xx
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Server error {response.status_code}",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()

            logger.info(
                "Картинка отправлена в WB | test_id=%s image_id=%s position=%s",
                self.test.id,
                image.id,
                image.position,
            )

        except httpx.HTTPError as e:
            logger.exception(
                "Ошибка отправки изображения в WB | test_id=%s image_id=%s: %s",
                self.test.id,
                image.id,
                e,
            )
            raise

        except Exception as e:
            logger.exception(
                "Неожиданная ошибка отправки изображения | test_id=%s image_id=%s: %s",
                self.test.id,
                image.id,
                e,
            )
            raise

        finally:
            try:
                image.image.close()
            except Exception:
                pass

    def process(self):
        try:
            self._process_internal()
        except Exception as e:
            logger.exception("Ошибка обработки теста | test_id=%s", self.test.id)
            self._add_error_safe(str(e))

    def _process_internal(self):
        logger.info("Старт теста test_id=%s", self.test.id)

        if self.test.status != self.test.Status.ACTIVE:
            logger.info("Тест не активен | test_id=%s", self.test.id)
            return
        now = timezone.now()

        if self.test.started_at is None:
            updated = (
                Test.objects
                .filter(pk=self.test.pk, status=Test.Status.ACTIVE, started_at__isnull=True)
                .update(started_at=now)
            )
            if updated:
                self.test.started_at = now
                logger.info(
                    "Установлено время старта теста в менеджере | test_id=%s started_at=%s",
                    self.test.id,
                    now,
                )

        if self.test.set_pause:
            with transaction.atomic():
                test = (
                    Test.objects
                    .select_for_update(skip_locked=True)
                    .select_related("current_image")
                    .filter(pk=self.test.pk)
                    .first()
                )

                if not test:
                    return

                if not test.set_pause:
                    return

                image = test.current_image

                if image:
                    # --- baseline check
                    if (
                            image.baseline_views is None
                            or image.baseline_clicks is None
                            or image.date_baseline is None
                            or image.started_at is None
                    ):
                        if not set_baseline_point(image):
                            test.add_error("Не удалось установить baseline при pause")
                            return

                    result = calculate_image_delta(image)

                    if result is None:
                        test.add_error("Не удалось посчитать дельту при pause")
                        return

                    delta_views, delta_clicks = result

                    projected_total_views = image.total_views + delta_views

                    close_image_session(image, delta_views, delta_clicks)

                    image.total_views = projected_total_views
                    image.total_clicks += delta_clicks
                    image.rounds_passed += 1

                    if image.total_views >= test.max_impressions_per_image:
                        image.status = Image.Status.DONE

                    image.save(update_fields=[
                        "total_views",
                        "total_clicks",
                        "rounds_passed",
                        "status",
                    ])

                    # обновляем baseline, чтобы не было повторного подсчёта
                    if not set_baseline_point(image):
                        test.add_error("Не удалось обновить baseline при pause")
                        return

                test.status = Test.Status.PAUSED
                test.set_pause = False
                test.save(update_fields=["status", "set_pause"])

                return


        if not sync_campaign_daily_stats(self.test):
            self._add_error_safe("Не удалось получить статистику WB")
            return

        image_to_send = None
        pending_switch = None
        pending_start = None

        with transaction.atomic():
            test = (
                Test.objects
                .select_for_update(skip_locked=True)
                .select_related("wb_token")
                .filter(pk=self.test.pk)
                .first()
            )

            # если не смогли взять (уже обрабатывается)
            if not test:
                logger.info("Тест уже обрабатывается | test_id=%s", self.test.id)
                return

            if test.status != Test.Status.ACTIVE:
                logger.info("Тест уже не активен после lock | test_id=%s", self.test.id)
                return

            if not test.current_image:
                eligible_images = list(
                    test.images.filter(
                        status=Image.Status.PENDING,
                        total_views__lt=test.max_impressions_per_image,
                    ).order_by("position")
                )

                if len(eligible_images) == 1:
                    test.status = Test.Status.FINISHED
                    test.current_image = None
                    test.finished_at = now
                    test.save(update_fields=["status", "current_image", "finished_at"])

                    logger.info(
                        "Тест завершён: для сравнения осталось 1 изображение | test_id=%s image_id=%s",
                        test.id,
                        eligible_images[0].id,
                    )
                    return

                next_image = eligible_images[0] if eligible_images else None

                if not next_image:
                    test.status = Test.Status.FINISHED
                    test.finished_at = now
                    test.save(update_fields=["status", "finished_at"])

                    logger.info("Тест завершён: нет доступных картинок | test_id=%s", test.id)
                    return

                image_to_send = next_image
                pending_start = {
                    "next_image_id": next_image.id,
                }

            else:
                image = test.current_image

                if (
                    image.baseline_views is None
                    or image.baseline_clicks is None
                    or image.date_baseline is None
                    or image.started_at is None
                ):
                    if not set_baseline_point(image):
                        logger.warning(
                            "Не удалось получить статистику за текущий день из базы данных | test_id=%s image_id=%s",
                            test.id, image.id
                        )
                        test.add_error(
                            "Не удалось получить статистику за текущий день из базы данных, возможно её не удалось получить из WB")
                        return

                # После resume у current_image может не быть открытой сессии.
                # open_image_session идемпотентен и создаст сессию только при её отсутствии.
                open_image_session(image)

                result = calculate_image_delta(image)

                if result is None:
                    logger.warning(
                        "Пропуск тика из-за некорректной дельты | test_id=%s image_id=%s",
                        test.id,
                        image.id,
                    )
                    test.add_error("Не удалось корректно высчитать результат")
                    return

                delta_views, delta_clicks = result
                projected_total_views = image.total_views + delta_views
                views_limit_reached = delta_views >= test.impressions_per_cycle
                time_limit_reached = (now - image.started_at).total_seconds() >= test.time_per_cycle
                image_limit_reached = projected_total_views >= test.max_impressions_per_image

                if not (views_limit_reached or time_limit_reached or image_limit_reached):
                    logger.info(
                        "Ротация не нужна | test_id=%s image_id=%s delta_views=%s elapsed=%.2f",
                        test.id,
                        image.id,
                        delta_views,
                        (now - image.started_at).total_seconds(),
                    )
                    return

                logger.info(
                    "Меняем картинку | test_id=%s image_id=%s delta_views=%s delta_clicks=%s",
                    test.id,
                    image.id,
                    delta_views,
                    delta_clicks,
                )

                eligible_images = list(
                    test.images.filter(
                        status=Image.Status.PENDING,
                        total_views__lt=test.max_impressions_per_image,
                    ).order_by("position")
                )

                if projected_total_views >= test.max_impressions_per_image:
                    eligible_images = [img for img in eligible_images if img.pk != image.pk]

                if len(eligible_images) == 1:
                    close_image_session(image, delta_views, delta_clicks)
                    image.total_views = projected_total_views
                    image.total_clicks += delta_clicks
                    image.rounds_passed += 1
                    if image.total_views >= test.max_impressions_per_image:
                        image.status = Image.Status.DONE
                    image.save(update_fields=[
                        "total_views",
                        "total_clicks",
                        "rounds_passed",
                        "status",
                    ])

                    test.status = Test.Status.FINISHED
                    test.current_image = None
                    test.finished_at = now
                    test.save(update_fields=["status", "current_image", "finished_at"])

                    logger.info(
                        "Тест завершён: для сравнения осталась 1 картинка | test_id=%s image_id=%s",
                        test.id,
                        eligible_images[0].id,
                    )
                    return

                first_image = eligible_images[0] if eligible_images else None
                next_image = None
                if eligible_images:
                    after_current = [img for img in eligible_images if img.position > image.position]
                    next_image = after_current[0] if after_current else first_image

                if not next_image:
                    close_image_session(image, delta_views, delta_clicks)
                    image.total_views = projected_total_views
                    image.total_clicks += delta_clicks
                    image.rounds_passed += 1
                    if image.total_views >= test.max_impressions_per_image:
                        image.status = Image.Status.DONE
                    test.status = Test.Status.FINISHED
                    test.current_image = None
                    test.finished_at = now
                    image.save(update_fields=[
                        "total_views",
                        "total_clicks",
                        "rounds_passed",
                        "status",
                    ])
                    test.save(update_fields=["status", "current_image", "finished_at"])

                    logger.info("Тест завершён: следующей картинки нет | test_id=%s", test.id)
                    return

                if next_image.pk == image.pk:
                    close_image_session(image, delta_views, delta_clicks)
                    image.total_views = projected_total_views
                    image.total_clicks += delta_clicks
                    image.rounds_passed += 1
                    if image.total_views >= test.max_impressions_per_image:
                        image.status = Image.Status.DONE
                    image.save(update_fields=[
                        "total_views",
                        "total_clicks",
                        "rounds_passed",
                        "status",
                    ])

                    test.status = Test.Status.FINISHED
                    test.current_image = None
                    test.finished_at = now
                    test.save(update_fields=["status", "current_image", "finished_at"])

                    logger.info(
                        "Тест завершён: для сравнения осталась 1 картинка | test_id=%s image_id=%s",
                        test.id,
                        image.id,
                    )
                    return

                image_to_send = next_image
                pending_switch = {
                    "old_image_id": image.id,
                    "next_image_id": next_image.id,
                    "delta_views": delta_views,
                    "delta_clicks": delta_clicks,
                    "projected_total_views": projected_total_views,
                }

        if not image_to_send:
            return

        try:
            self._send_image(image_to_send)
        except Exception as e:
            logger.exception(
                "Ошибка отправки изображения в WB | test_id=%s image_id=%s",
                self.test.id,
                image_to_send.id,
            )
            self._add_error_safe(f"Ошибка отправки изображения в WB: {e}")
            return

        with transaction.atomic():
            test = (
                Test.objects
                .select_for_update(skip_locked=True)
                .filter(pk=self.test.pk)
                .first()
            )

            if not test:
                logger.warning(
                    "WB ok, но фиксация во второй фазе пропущена: test row locked | test_id=%s",
                    self.test.id,
                )
                self._add_error_safe(
                    "WB принял картинку, но фиксация в БД не выполнена из-за блокировки. Тик будет повторен."
                )
                return

            if test.status != Test.Status.ACTIVE:
                logger.info("Тест не активен во второй фазе | test_id=%s", self.test.id)
                return

            if pending_start:
                if test.current_image_id is not None:
                    if test.current_image_id == pending_start["next_image_id"]:
                        logger.info(
                            "Старт уже применён другим воркером | test_id=%s image_id=%s",
                            test.id,
                            test.current_image_id,
                        )
                    else:
                        logger.error(
                            "WB принял картинку, но current_image уже другой | test_id=%s expected_image_id=%s actual_image_id=%s",
                            test.id,
                            pending_start["next_image_id"],
                            test.current_image_id,
                        )
                        test.add_error(
                            "Возможен рассинхрон: WB принял картинку, но в БД уже установлен другой current_image"
                        )
                    return

                next_image = Image.objects.select_for_update().filter(pk=pending_start["next_image_id"]).first()
                if not next_image:
                    logger.warning("Старт пропущен: next_image не найден | test_id=%s", test.id)
                    return

                if not set_baseline_point(next_image):
                    logger.warning(
                        "WB ok, но baseline не установлен | test_id=%s image_id=%s",
                        test.id,
                        next_image.id,
                    )
                    test.current_image = next_image
                    test.save(update_fields=["current_image"])
                    self._add_error_safe(
                        "WB принял картинку, но baseline пока не установлен (будет доустановлен на следующем тике)"
                    )
                    return

                open_image_session(next_image)
                test.current_image = next_image
                test.save(update_fields=["current_image"])
                return

            if not pending_switch:
                return

            if not test.current_image or test.current_image_id != pending_switch["old_image_id"]:
                logger.warning(
                    "Переключение отменено: current_image изменился во второй фазе | test_id=%s",
                    test.id,
                )
                return

            image = Image.objects.select_for_update().get(pk=pending_switch["old_image_id"])
            next_image = Image.objects.select_for_update().get(pk=pending_switch["next_image_id"])

            delta_views = pending_switch["delta_views"]
            delta_clicks = pending_switch["delta_clicks"]

            close_image_session(image, delta_views, delta_clicks)

            image.total_views = pending_switch["projected_total_views"]
            image.total_clicks += delta_clicks
            image.rounds_passed += 1

            if image.total_views >= test.max_impressions_per_image:
                image.status = Image.Status.DONE
                logger.info(
                    "Картинка достигла лимита и завершена | test_id=%s image_id=%s",
                    test.id,
                    image.id,
                )

            image.save(update_fields=[
                "total_views",
                "total_clicks",
                "rounds_passed",
                "status",
            ])

            test_update_fields = ["current_image"]
            first_image = test.images.filter(
                status=Image.Status.PENDING,
                total_views__lt=test.max_impressions_per_image,
            ).order_by("position").first()

            if first_image and next_image.pk == first_image.pk:
                closed_cycle = test.current_cycle
                run_ctr(test, cycle_number=closed_cycle)
                test.current_cycle += 1
                test_update_fields.append("current_cycle")
                logger.info(
                    "Новый цикл | test_id=%s current_cycle=%s",
                    test.id,
                    test.current_cycle,
                )

            if not set_baseline_point(next_image):
                logger.warning(
                    "WB ok, но baseline не установлен | test_id=%s image_id=%s",
                    test.id,
                    next_image.id,
                )
                test.current_image = next_image
                test.save(update_fields=test_update_fields)
                self._add_error_safe(
                    "WB принял картинку, но baseline пока не установлен (будет доустановлен на следующем тике)"
                )
                return

            open_image_session(next_image)
            test.current_image = next_image
            test.save(update_fields=test_update_fields)
