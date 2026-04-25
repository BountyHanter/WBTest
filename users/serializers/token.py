from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        if not user.is_verified:
            raise serializers.ValidationError({
                "detail": "Email не подтверждён"
            })

        return data