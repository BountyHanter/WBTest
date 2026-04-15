# Подумать над шифрованием
from django.conf import settings
from django.db import models


class WBToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wb_tokens",
        verbose_name="Пользователь"
    )

    token = models.CharField(
        max_length=500,
        verbose_name="WB токен"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "WB токен"
        verbose_name_plural = "WB токены"

    def __repr__(self):
        return f"<WBToken id={self.id} user={self.user_id}>"
