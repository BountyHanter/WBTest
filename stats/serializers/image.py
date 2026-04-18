from rest_framework import serializers
from stats.models import Image


class ImageSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField(read_only=True)

    def get_is_current(self, obj):
        current_image_id = self.context.get("current_image_id")
        if current_image_id is None:
            return False
        return obj.id == current_image_id

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
            "is_current",
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
