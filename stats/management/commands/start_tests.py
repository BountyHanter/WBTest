import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand
from django.db import transaction, close_old_connections

from stats.models import Test
from stats.services.tests_manager import TestEngine

logger = logging.getLogger(__name__)

def _process_single_test(test_id: int) -> None:
    close_old_connections()  # 🔥 достаточно для потоков

    try:
        test = Test.objects.get(pk=test_id)
        TestEngine(test=test).process()

    except Exception:
        logger.exception("Ошибка обработки теста | test_id=%s", test_id)

    finally:
        try:
            Test.objects.filter(pk=test_id).update(is_processed=False)
        except Exception:
            logger.exception(
                "Не удалось сбросить is_processed | test_id=%s",
                test_id,
            )

class Command(BaseCommand):
    help = "Обрабатывает до 100 активных тестов"

    def handle(self, *args, **options):
        claimed_ids: list[int] = []

        try:
            with transaction.atomic():
                tests = list(
                    Test.objects
                    .select_for_update(skip_locked=True)
                    .filter(
                        status=Test.Status.ACTIVE,
                        is_processed=False,
                    )
                    .order_by("id")[:100]
                )

                if not tests:
                    self.stdout.write("Нет тестов для обработки")
                    return

                claimed_ids = [test.id for test in tests]

                Test.objects.filter(id__in=claimed_ids).update(is_processed=True)

            workers_count = max(1, min(10, len(claimed_ids)))

            self.stdout.write(
                f"Взято тестов: {len(claimed_ids)} | потоков: {workers_count}"
            )

            with ThreadPoolExecutor(max_workers=workers_count) as executor:
                futures = {
                    executor.submit(_process_single_test, test_id): test_id
                    for test_id in claimed_ids
                }

                for future in as_completed(futures):
                    test_id = futures[future]
                    try:
                        future.result()
                    except Exception:
                        logger.exception(
                            "Ошибка future | test_id=%s",
                            test_id,
                        )

        finally:
            if claimed_ids:
                try:
                    Test.objects.filter(id__in=claimed_ids).update(is_processed=False)
                except Exception:
                    logger.exception(
                        "Не удалось выполнить финальный сброс is_processed | test_ids=%s",
                        claimed_ids,
                    )