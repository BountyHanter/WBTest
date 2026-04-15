from rest_framework import serializers
from stats.models import Image


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = (
            "id",
            "test",

            # управление
            "position",
            "image",

            # статус
            "status",

            # агрегаты
            "total_views",
            "total_clicks",
            "rounds_passed",
            "wins_count",

            "started_at",

            # системные
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "test",
            "status",

            "total_views",
            "total_clicks",
            "rounds_passed",
            "wins_count",

            "started_at",

            "created_at",
            "updated_at",
        )