from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from stats.models import Test
from stats.serializers.test import TestSerializer, TestWithImagesSerializer


class TestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tests = (
            Test.objects
            .filter(user=request.user)
            .order_by("-created_at")
        )
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test = serializer.save(user=request.user)

        return Response(
            TestSerializer(test).data,
            status=status.HTTP_201_CREATED,
        )


class TestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Test.objects.get(pk=pk, user=request.user)
        except Test.DoesNotExist:
            raise NotFound("Тест не найден")

    def get(self, request, pk):
        test = self.get_object(request, pk)
        serializer = TestSerializer(test)
        return Response(serializer.data)

    def patch(self, request, pk):
        test = self.get_object(request, pk)

        serializer = TestSerializer(
            test,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, pk):
        test = self.get_object(request, pk)

        try:
            test.delete()
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        return Response(status=status.HTTP_204_NO_CONTENT)

class TestCreateWithImagesView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = TestWithImagesSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        test = serializer.save()

        return Response(
            TestSerializer(test).data,
            status=201
        )