from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.utils.verification import check_verification_token

User = get_user_model()


class VerifyEmailView(APIView):
    permission_classes = []

    def get(self, request):
        user_id = request.query_params.get("user_id")
        token = request.query_params.get("token")

        if not user_id or not token:
            return Response(
                {"detail": "user_id и token обязательны"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not check_verification_token(user, token):
            return Response(
                {"detail": "Неверный или устаревший токен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_verified = True
        user.save()

        return Response({"detail": "Email подтверждён"})