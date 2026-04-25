from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers.register import RegisterSerializer
from users.utils.send_verification import send_verification


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        send_verification(user)

        return Response(
            {
                "detail": "Письмо для подтверждения отправлено на email"
            },
            status=status.HTTP_201_CREATED
        )