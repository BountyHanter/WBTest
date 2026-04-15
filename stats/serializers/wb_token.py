from rest_framework import serializers

from stats.models import WBToken


class WBTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = WBToken
        fields = (
            "id",
            "token",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )
