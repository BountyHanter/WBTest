import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from config.utils.test_print import debug_response
from stats.models import Test
from stats.tests.utils.factories import create_user, create_wb_token


@pytest.mark.django_db
class TestTestActionsAPI:

    def create_test(self, user):
        return Test.objects.create(
            user=user,
            wb_token=create_wb_token(user=user),
            name="test",
            campaign_id=1,
            product_id=1,
            impressions_per_cycle=10,
            max_impressions_per_image=100,
            time_per_cycle=60,
        )

    # 🚀 START
    def test_start_from_draft(self):
        user = create_user(300)
        test = self.create_test(user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-start", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_200_OK

        test.refresh_from_db()
        assert test.status == Test.Status.ACTIVE

    def test_start_not_from_draft_fails(self):
        user = create_user(301)
        test = self.create_test(user)
        test.status = Test.Status.ACTIVE
        test.save()

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-start", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ⏸ PAUSE
    def test_pause_sets_flag(self):
        user = create_user(302)
        test = self.create_test(user)
        test.status = Test.Status.ACTIVE
        test.save()

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-pause", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_200_OK

        test.refresh_from_db()
        assert test.set_pause is True

    def test_pause_not_active_fails(self):
        user = create_user(303)
        test = self.create_test(user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-pause", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ▶ RESUME
    def test_resume_from_paused(self):
        user = create_user(304)
        test = self.create_test(user)
        test.status = Test.Status.PAUSED
        test.save()

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-resume", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_200_OK

        test.refresh_from_db()
        assert test.status == Test.Status.ACTIVE

    def test_resume_not_paused_fails(self):
        user = create_user(305)
        test = self.create_test(user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-resume", kwargs={"pk": test.id})
        response = client.post(url)

        debug_response(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST