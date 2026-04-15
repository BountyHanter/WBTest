from django.contrib.auth import authenticate
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            # Я убрал username из модели, но функция всё равно ожидает username в качестве ключа
            username=data["email"],
            password=data["password"]
        )

        if not user:
            raise serializers.ValidationError({
                "detail": "Неверный email или пароль"
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "Пользователь не активен"
            })

        data["user"] = user
        return data
