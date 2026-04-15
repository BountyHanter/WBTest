from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint, Q

from stats.models.stats import CampaignDailyStat
from stats.models.test import Test


class Image(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        DONE = "done", "Завершено"

    test = models.ForeignKey(
        "Test",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Тест"
    )

    position = models.PositiveIntegerField(verbose_name="Позиция")
    image = models.ImageField(
        upload_to="tests/images/",
        verbose_name="Изображение"
    )

    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.PENDING,
        verbose_name="Статус"
    )

    total_views = models.PositiveIntegerField(default=0, verbose_name="Всего показов")
    total_clicks = models.PositiveIntegerField(default=0, verbose_name="Всего кликов")

    baseline_views = models.PositiveIntegerField(null=True, blank=True, verbose_name="Baseline просмотров")
    baseline_clicks = models.PositiveIntegerField(null=True, blank=True, verbose_name="Baseline кликов")
    date_baseline = models.DateTimeField(null=True, blank=True, verbose_name="Время снимка")

    rounds_passed = models.PositiveIntegerField(default=0, verbose_name="Сколько кругов прошла картинка")
    wins_count = models.PositiveIntegerField(default=0, verbose_name="Счётчик побед")

    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Начало показа")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"
        constraints = [
            models.UniqueConstraint(fields=["test", "position"], name="unique_test_position")
        ]
        indexes = [
            models.Index(fields=["test", "status"]),
            models.Index(fields=["test", "position"]),
        ]
        ordering = ["position"]

    def __str__(self):
        return f"{self.test_id} | {self.position}"

    def __repr__(self):
        return (
            f"<Image "
            f"id={self.id} "
            f"test_id={self.test_id} "
            f"pos={self.position} "
            f"status={self.status} "
            f"views={self.total_views} "
            f"clicks={self.total_clicks} "
            f"rounds={self.rounds_passed} "
            f"wins={self.wins_count} "
            f"baseline_views={self.baseline_views} "
            f"baseline_clicks={self.baseline_clicks} "
            f">"
        )

    def clean(self):
        if self.position < 1:
            raise ValidationError({"position": "Позиция должна быть больше 0"})

        if not self.pk:
            if self.test.status != self.test.Status.DRAFT:
                raise ValidationError("Нельзя добавлять изображения после запуска теста")

        exists = type(self).objects.filter(
            test=self.test,
            position=self.position
        ).exclude(pk=self.pk).exists()

        if exists:
            raise ValidationError({"position": "Позиция уже занята"})

        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if not old:
                return

            if old.test.status != self.test.Status.DRAFT:
                errors = {}

                if old.position != self.position:
                    errors["position"] = "Нельзя изменять после запуска теста"

                if old.image != self.image:
                    errors["image"] = "Нельзя изменять после запуска теста"

                if errors:
                    raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.test.status != self.test.Status.DRAFT:
            raise ValidationError("Нельзя удалять изображение после запуска теста")
        return super().delete(*args, **kwargs)


class ImageShowStat(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        verbose_name="Тест"
    )
    image = models.ForeignKey(
        Image,
        on_delete=models.CASCADE,
        verbose_name="Изображение"
    )
    cycle_number = models.PositiveIntegerField(
        verbose_name="Номер цикла"
    )

    start_views = models.PositiveIntegerField(
        verbose_name="Показы на старте"
    )
    start_clicks = models.PositiveIntegerField(
        verbose_name="Клики на старте"
    )
    started_at = models.DateTimeField(
        verbose_name="Время старта"
    )
    start_day = models.ForeignKey(
        CampaignDailyStat,
        on_delete=models.SET_NULL,
        null=True,
        related_name="start_sessions"
    )

    end_views = models.PositiveIntegerField(
        verbose_name="Показы на конце",
        null=True,
        blank=True,
    )
    end_clicks = models.PositiveIntegerField(
        verbose_name="Клики на конце",
        null=True,
        blank=True,
    )
    finished_at = models.DateTimeField(
        verbose_name="Время завершения",
        null=True,
        blank=True,
    )
    end_day = models.ForeignKey(
        CampaignDailyStat,
        on_delete=models.SET_NULL,
        null=True,
        related_name="end_sessions"
    )

    class Meta:
        verbose_name = "Сеанс показа изображения"
        verbose_name_plural = "Сеансы показа изображений"

        constraints = [
            UniqueConstraint(
                fields=["image"],
                condition=Q(finished_at__isnull=True),
                name="unique_open_session_per_image"
            )
        ]
