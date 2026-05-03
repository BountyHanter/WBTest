from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.serializers.reset_password import PasswordResetSerializer, PasswordResetConfirmSerializer
from users.utils.reset_password import send_password_reset
from users.utils.verification import check_verification_token

User = get_user_model()


class PasswordResetView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()

        if user:
            send_password_reset(user)

        return Response(
            {"detail": "Если пользователь существует, письмо отправлено"},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not check_verification_token(user, token):
            return Response(
                {"detail": "Неверный или устаревший токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.save()

        return Response(
            {"detail": "Пароль успешно изменён"},
            status=status.HTTP_200_OK,
        )