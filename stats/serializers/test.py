from rest_framework import serializers
from django.db import transaction

from stats.models import Test, Image


class TestSerializer(serializers.ModelSerializer):
    preview_image = serializers.SerializerMethodField()

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
            "set_pause",

            "preview_image",

            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "preview_image",
            "created_at",
            "updated_at",
        )

    def get_preview_image(self, obj):
        # 1. если есть текущая
        if obj.current_image:
            return obj.current_image.image.url

        # 2. иначе первая по позиции
        image = obj.images.order_by("position").first()
        if image:
            return image.image.url

        return None

class TestWithImagesSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )

    positions = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Test
        fields = (
            "id",
            "name",
            "campaign_id",
            "product_id",
            "wb_token",
            "impressions_per_cycle",
            "max_impressions_per_image",
            "time_per_cycle",
            "images",
            "positions",
        )

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        positions = validated_data.pop("positions", [])

        user = self.context["request"].user

        with transaction.atomic():
            test = Test.objects.create(
                user=user,
                **validated_data,
            )

            for i, image in enumerate(images):
                position = positions[i] if i < len(positions) else i + 1

                Image.objects.create(
                    test=test,
                    image=image,
                    position=position,
                )

        return test