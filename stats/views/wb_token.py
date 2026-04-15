from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound

from stats.models import WBToken, Test
from stats.serializers.wb_token import WBTokenSerializer


class WBTokenListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tokens = WBToken.objects.filter(user=request.user).order_by("-created_at")
        serializer = WBTokenSerializer(tokens, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WBTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        token = serializer.save(user=request.user)
        return Response(
            WBTokenSerializer(token).data,
            status=status.HTTP_201_CREATED,
        )

class WBTokenDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return WBToken.objects.get(pk=pk, user=request.user)
        except WBToken.DoesNotExist:
            raise NotFound({"detail": "Токен не найден"})

    def get(self, request, pk):
        token = self.get_object(request, pk)
        serializer = WBTokenSerializer(token)
        return Response(serializer.data)

    def patch(self, request, pk):
        token = self.get_object(request, pk)

        serializer = WBTokenSerializer(
            token,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, pk):
        token = self.get_object(request, pk)

        if Test.objects.filter(wb_token=token).exists():
            raise ValidationError(
                {"detail": "Нельзя удалить токен, который используется в тестах."}
            )

        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)