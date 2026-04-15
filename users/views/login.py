from rest_framework.response import Response
from rest_framework.views import APIView

from config.utils.jwt_token import get_tokens_for_user
from users.serializers.login import LoginSerializer


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response(tokens)
