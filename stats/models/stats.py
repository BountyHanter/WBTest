from django.db import models

from stats.models.test import Test


class CampaignDailyStat(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="daily_stats",
        verbose_name="Тест"
    )

    date = models.DateField(
        verbose_name="Дата (WB timezone)"
    )

    views = models.PositiveIntegerField(
        default=0,
        verbose_name="Показы за день"
    )

    clicks = models.PositiveIntegerField(
        default=0,
        verbose_name="Клики за день"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Дневная статистика изображения"
        verbose_name_plural = "Дневная статистика изображений"

        constraints = [
            models.UniqueConstraint(
                fields=["test", "date"],
                name="unique_test_date"
            )
        ]

        indexes = [
            models.Index(fields=["test", "date"]),
        ]
    def __str__(self):
        return f"{self.test.id} | {self.date} | views={self.views}"