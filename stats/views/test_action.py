from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError

from stats.models import Test


class BaseTestActionView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Test.objects.get(pk=pk, user=request.user)
        except Test.DoesNotExist:
            raise NotFound("Тест не найден")


# START
class TestStartView(BaseTestActionView):
    def post(self, request, pk):
        test = self.get_object(request, pk)

        if test.status != Test.Status.DRAFT:
            raise ValidationError(
                {"detail": "Можно запустить только тест в статусе draft"}
            )

        test.status = Test.Status.ACTIVE
        test.started_at = timezone.now()
        test.save(update_fields=["status", "started_at"])

        return Response({"detail": "Тест запущен"})


# PAUSE
class TestPauseView(BaseTestActionView):
    def post(self, request, pk):
        test = self.get_object(request, pk)

        if test.set_pause:
            return Response({"detail": "Тест будет остановлен"})

        if test.status != Test.Status.ACTIVE:
            raise ValidationError(
                {"detail": "Можно поставить на паузу только active тест"}
            )

        test.set_pause = True
        test.save(update_fields=["set_pause"])

        return Response({"detail": "Тест будет остановлен"})


# RESUME
class TestResumeView(BaseTestActionView):
    def post(self, request, pk):
        test = self.get_object(request, pk)

        if test.status != Test.Status.PAUSED:
            raise ValidationError(
                {"detail": "Можно возобновить только paused тест"}
            )

        test.status = Test.Status.ACTIVE
        update_fields = ["status"]
        if test.set_pause:
            test.set_pause = False
            update_fields.append("set_pause")
        test.save(update_fields=update_fields)

        return Response({"detail": "Тест возобновлён"})