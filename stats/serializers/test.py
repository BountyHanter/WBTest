from rest_framework import serializers

from stats.models import Test


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = (
            "id",
            "name",
            "campaign_id",
            "product_id",
            "wb_token",
            "status",

            "impressions_per_cycle",
            "max_impressions_per_image",
            "time_per_cycle",

            "current_image",

            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "current_image",
            "created_at",
            "updated_at",
        )