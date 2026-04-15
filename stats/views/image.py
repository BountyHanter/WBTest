from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from stats.models import Test, Image
from stats.serializers.image import ImageSerializer

class BaseTestImageView(APIView):
    permission_classes = [IsAuthenticated]

    def get_test(self, request, test_id):
        try:
            return Test.objects.get(pk=test_id, user=request.user)
        except Test.DoesNotExist:
            raise NotFound("Тест не найден")

    def check_draft(self, test):
        if test.status != Test.Status.DRAFT:
            raise ValidationError("Можно изменять только draft тест")

class TestImageListCreateView(BaseTestImageView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, test_id):
        test = self.get_test(request, test_id)

        images = test.images.all()
        serializer = ImageSerializer(images, many=True)
        return Response(serializer.data)

    def post(self, request, test_id):
        test = self.get_test(request, test_id)
        self.check_draft(test)

        serializer = ImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            image = serializer.save(test=test)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)

        return Response(
            ImageSerializer(image).data,
            status=status.HTTP_201_CREATED,
        )

class TestImageDetailView(BaseTestImageView):
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, request, test_id, image_id):
        try:
            return Image.objects.get(
                pk=image_id,
                test_id=test_id,
                test__user=request.user
            )
        except Image.DoesNotExist:
            raise NotFound("Изображение не найдено")

    def patch(self, request, test_id, image_id):
        image = self.get_object(request, test_id, image_id)
        self.check_draft(image.test)

        serializer = ImageSerializer(
            image,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)

        return Response(serializer.data)

    def delete(self, request, test_id, image_id):
        image = self.get_object(request, test_id, image_id)
        self.check_draft(image.test)

        try:
            image.delete()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)

        return Response(status=status.HTTP_204_NO_CONTENT)

class TestImageReorderView(BaseTestImageView):

    def post(self, request, test_id):
        test = self.get_test(request, test_id)
        self.check_draft(test)

        items = request.data.get("items")

        if not isinstance(items, list) or not items:
            raise ValidationError({"items": "Должен быть список"})

        ids = [item.get("id") for item in items]
        positions = [item.get("position") for item in items]

        if len(ids) != len(set(ids)):
            raise ValidationError("Дубликаты id")

        if len(positions) != len(set(positions)):
            raise ValidationError("Дубликаты position")

        images = list(Image.objects.filter(test=test, id__in=ids))

        if len(images) != len(ids):
            raise ValidationError("Некоторые изображения не найдены")

        image_map = {img.id: img for img in images}

        try:
            with transaction.atomic():
                # временный сдвиг
                for img in images:
                    img.position += 1000
                    img.save(update_fields=["position"])

                # финальные позиции
                for item in items:
                    img = image_map[item["id"]]
                    img.position = item["position"]
                    img.save(update_fields=["position"])
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)

        return Response({"detail": "Порядок обновлён"})