import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from config.utils.test_print import debug_response
from stats.models import Test
from stats.tests.utils.factories import create_user, create_wb_token


@pytest.mark.django_db
class TestTestAPI:

    def test_create_test(self):
        user = create_user(200)
        wb_token = create_wb_token(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-list")

        response = client.post(
            url,
            data={
                "name": "My test",
                "campaign_id": 1,
                "product_id": 1,
                "wb_token": wb_token.id,
                "impressions_per_cycle": 10,
                "max_impressions_per_image": 100,
                "time_per_cycle": 60,
            },
            format="json",
        )

        debug_response(response)

        assert response.status_code == status.HTTP_201_CREATED
        assert Test.objects.filter(user=user).exists()

    def test_get_only_own_tests(self):
        user = create_user(201)
        other_user = create_user(202)

        wb_token = create_wb_token(user=user)

        Test.objects.create(
            user=user,
            wb_token=wb_token,
            name="my",
            campaign_id=1,
            product_id=1,
            impressions_per_cycle=10,
            max_impressions_per_image=100,
            time_per_cycle=60,
        )

        Test.objects.create(
            user=other_user,
            wb_token=create_wb_token(user=other_user),
            name="foreign",
            campaign_id=1,
            product_id=1,
            impressions_per_cycle=10,
            max_impressions_per_image=100,
            time_per_cycle=60,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("test-list"))
        debug_response(response)

        assert len(response.data) == 1

    def test_delete_not_draft_fails(self):
        user = create_user(203)
        wb_token = create_wb_token(user=user)

        test = Test.objects.create(
            user=user,
            wb_token=wb_token,
            name="test",
            campaign_id=1,
            product_id=1,
            impressions_per_cycle=10,
            max_impressions_per_image=100,
            time_per_cycle=60,
            status=Test.Status.ACTIVE,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(
            reverse("test-detail", kwargs={"pk": test.id})
        )
        debug_response(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST