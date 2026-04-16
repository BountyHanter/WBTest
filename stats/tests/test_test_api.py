import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from config.utils.test_print import debug_response
from stats.models import Test, Image
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


@pytest.mark.django_db
class TestTestFullCreateAPI:

    def create_file(self):
        return SimpleUploadedFile(
            "test.gif",
            (
                b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
                b"\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00"
                b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
            ),
            content_type="image/gif",
        )

    def test_create_test_with_images(self):
        user = create_user(600)
        token = create_wb_token(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-full-create")

        response = client.post(
            url,
            data={
                "name": "test",
                "campaign_id": 1,
                "product_id": 1,
                "wb_token": token.id,
                "impressions_per_cycle": 10,
                "max_impressions_per_image": 100,
                "time_per_cycle": 60,

                "images": [
                    self.create_file(),
                    self.create_file(),
                ],
                "positions": [1, 2],
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == status.HTTP_201_CREATED

        test = Test.objects.first()
        assert test is not None

        images = Image.objects.filter(test=test)
        assert images.count() == 2

    def test_create_without_positions(self):
        user = create_user(601)
        token = create_wb_token(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-full-create")

        response = client.post(
            url,
            data={
                "name": "test",
                "campaign_id": 1,
                "product_id": 1,
                "wb_token": token.id,
                "impressions_per_cycle": 10,
                "max_impressions_per_image": 100,
                "time_per_cycle": 60,

                "images": [
                    self.create_file(),
                    self.create_file(),
                ],
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == 201

        test = Test.objects.first()
        images = Image.objects.filter(test=test).order_by("position")

        assert images[0].position == 1
        assert images[1].position == 2

    def test_atomic_rollback_on_error(self):
        user = create_user(602)
        token = create_wb_token(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-full-create")

        response = client.post(
            url,
            data={
                "name": "test",
                "campaign_id": 1,
                "product_id": 1,
                "wb_token": token.id,
                "impressions_per_cycle": 10,
                "max_impressions_per_image": 100,
                "time_per_cycle": 60,

                "images": [
                    self.create_file(),
                ],
                "positions": ["bad_position"],  # ❌ ошибка
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == 400

        # 🔥 ничего не должно создаться
        assert Test.objects.count() == 0
        assert Image.objects.count() == 0

    def test_unauthorized(self):
        client = APIClient()

        url = reverse("test-full-create")

        response = client.post(url)

        debug_response(response)

        assert response.status_code == 401

    def test_create_without_images(self):
        user = create_user(603)
        token = create_wb_token(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("test-full-create")

        response = client.post(
            url,
            data={
                "name": "test",
                "campaign_id": 1,
                "product_id": 1,
                "wb_token": token.id,
                "impressions_per_cycle": 10,
                "max_impressions_per_image": 100,
                "time_per_cycle": 60,
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == 201

        assert Test.objects.count() == 1
        assert Image.objects.count() == 0