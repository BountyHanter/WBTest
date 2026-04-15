from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="imageshowstat",
            name="end_clicks",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Клики на конце",
            ),
        ),
        migrations.AlterField(
            model_name="imageshowstat",
            name="end_views",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Показы на конце",
            ),
        ),
        migrations.AlterField(
            model_name="imageshowstat",
            name="finished_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Время завершения",
            ),
        ),
    ]
