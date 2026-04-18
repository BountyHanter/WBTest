from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from stats.models.token import WBToken


class Test(models.Model):
    MAX_ERRORS = 3

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активен"
        PAUSED = "paused", "На паузе"
        FINISHED = "finished", "Завершён"
        ERROR = "error", "Ошибка"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tests",
        verbose_name="Пользователь"
    )

    campaign_id = models.BigIntegerField(verbose_name="ID кампании WB")
    product_id = models.BigIntegerField(verbose_name="ID товара (Артикул)")
    wb_token = models.ForeignKey(
        WBToken,
        on_delete=models.CASCADE,
        related_name="tests",
        verbose_name="WB токен"
    )
    name = models.CharField(max_length=255, verbose_name="Название теста")

    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.DRAFT,
        verbose_name="Статус"
    )

    set_pause = models.BooleanField(
        default=False,
        verbose_name="Флаг для установки на паузу"
    )

    error_counts = models.PositiveIntegerField(default=0, verbose_name="Количество ошибочных запусков")

    last_error = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    error_log = models.JSONField(default=list, blank=True, null=True)

    impressions_per_cycle = models.PositiveIntegerField(verbose_name="Показов на цикл")
    max_impressions_per_image = models.PositiveIntegerField(verbose_name="Макс. показов на изображение")
    time_per_cycle = models.PositiveIntegerField(verbose_name="Время на цикл (сек)")
    current_views = models.PositiveIntegerField(default=0, verbose_name="Показов на текущий момент")
    current_cycle = models.PositiveIntegerField(default=0, verbose_name="Номер цикла")

    current_image = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Текущее изображение"
    )

    is_processed = models.BooleanField(verbose_name="Статус обработки теста за проход", default=False)
    processed_round = models.PositiveBigIntegerField(
        default=0,
        db_index=True,
        verbose_name="Номер раунда планировщика, в котором тест уже обработан",
    )

    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата старта")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Тест"
        verbose_name_plural = "Тесты"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return self.name or f"Test {self.id}"

    def __repr__(self):
        return (
            f"<Test "
            f"id={self.id} "
            f"status={self.status} "
            f"impr_cycle={self.impressions_per_cycle} "
            f"max_impr={self.max_impressions_per_image} "
            f"time_cycle={self.time_per_cycle}s "
            f"current_views={self.current_views} "
            f"current_image_id={self.current_image_id} "
            f"started_at={self.started_at} "
            f"finished_at={self.finished_at} "
            f">"
        )

    def clean(self):
        if self.impressions_per_cycle <= 0:
            raise ValidationError({"impressions_per_cycle": "Должно быть больше 0"})

        if self.max_impressions_per_image <= 0:
            raise ValidationError({"max_impressions_per_image": "Должно быть больше 0"})

        if self.time_per_cycle <= 0:
            raise ValidationError({"time_per_cycle": "Должно быть больше 0"})

        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if not old:
                return

            if old.status != self.Status.DRAFT:
                restricted_fields = [
                    "campaign_id",
                    "product_id",
                    "wb_token",
                    "impressions_per_cycle",
                    "max_impressions_per_image",
                    "time_per_cycle",
                ]

                errors = {}

                for field in restricted_fields:
                    if getattr(old, field) != getattr(self, field):
                        errors[field] = "Нельзя изменять после запуска теста"

                if errors:
                    raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.ACTIVE:
            raise ValidationError("Нельзя удалить тест если он Активен")
        return super().delete(*args, **kwargs)

    def _register_error(self):
        self.error_counts += 1

        if self.error_counts >= self.MAX_ERRORS:
            if self.status != self.Status.ERROR:
                self.status = self.Status.ERROR

            if not self.finished_at:
                self.finished_at = timezone.now()

    def add_error(self, message: str):
        now = timezone.now().isoformat()

        if self.error_log is None:
            self.error_log = []

        # важно: мутируем именно self.error_log
        self.error_log.append({
            "time": now,
            "message": message,
        })

        # чтобы Django точно увидел изменение
        self.error_log = list(self.error_log)

        self.last_error = message

        self._register_error()

        self.save(update_fields=[
            "error_log",
            "last_error",
            "error_counts",
            "status",
            "finished_at",
        ])

class SchedulerState(models.Model):
    current_round = models.PositiveBigIntegerField(
        default=1,
        verbose_name="Текущий раунд планировщика",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Состояние планировщика"
        verbose_name_plural = "Состояния планировщика"

    @classmethod
    def get_solo(cls):
        state, _ = cls.objects.get_or_create(pk=1, defaults={"current_round": 1})
        return state

    @classmethod
    def increment_round(cls):
        with transaction.atomic():
            state, _ = cls.objects.select_for_update().get_or_create(
                pk=1,
                defaults={"current_round": 1},
            )
            state.current_round += 1
            state.save()
            return state.current_round

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Нельзя удалять singleton SchedulerState")

    def __str__(self):
        return f"round={self.current_round}"
