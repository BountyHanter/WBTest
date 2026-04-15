from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.utils.jwt_token import get_tokens_for_user
from users.serializers.register import RegisterSerializer


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        tokens = get_tokens_for_user(user)

        return Response(tokens, status=status.HTTP_201_CREATED)
