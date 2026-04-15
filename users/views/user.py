from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers.user import UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    # def patch(self, request):
    #     user = request.user
    #
    #     user.save()
    #
    #     return Response(UserSerializer(user).data)