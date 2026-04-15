import json
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from stats.models import Image, Test as TestModel
from stats.tests.utils.factories import create_user, create_wb_token


def debug_response(response):
    if getattr(pytest, "DEBUG", False):
        try:
            data = response.json()
        except Exception:
            data = response.content.decode()

        print(json.dumps(
            {"status": response.status_code, "data": data},
            ensure_ascii=False,
            indent=4,
        ))


@pytest.mark.django_db
class TestImageAPI:

    def create_test(self, user, status=TestModel.Status.DRAFT):
        return TestModel.objects.create(
            user=user,
            wb_token=create_wb_token(user=user),
            name="test",
            campaign_id=1,
            product_id=1,
            impressions_per_cycle=10,
            max_impressions_per_image=100,
            time_per_cycle=60,
            status=status,
        )

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

    def create_image(self, test):
        return Image.objects.create(
            test=test,
            position=1,
            image=self.create_file(),
        )

    # ✅ CREATE
    def test_create_image(self):
        user = create_user(500)
        test = self.create_test(user)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-list", kwargs={"test_id": test.id})

        response = client.post(
            url,
            data={
                "position": 1,
                "image": self.create_file(),
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == status.HTTP_201_CREATED
        assert Image.objects.filter(test=test).exists()

    # ❌ CREATE не в draft
    def test_create_image_not_draft_fails(self):
        user = create_user(501)
        test = self.create_test(user, status=TestModel.Status.ACTIVE)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-list", kwargs={"test_id": test.id})

        response = client.post(
            url,
            data={
                "position": 1,
                "image": self.create_file(),
            },
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # 📄 LIST
    def test_list_images(self):
        user = create_user(502)
        test = self.create_test(user)

        self.create_image(test)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-list", kwargs={"test_id": test.id})
        response = client.get(url)

        debug_response(response)

        assert response.status_code == 200
        assert len(response.data) == 1

    # 🔧 PATCH
    def test_patch_image(self):
        user = create_user(503)
        test = self.create_test(user)

        image = self.create_image(test)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-detail", kwargs={
            "test_id": test.id,
            "image_id": image.id
        })

        response = client.patch(
            url,
            data={"position": 2},
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == 200

        image.refresh_from_db()
        assert image.position == 2

    # ❌ PATCH не в draft
    def test_patch_image_not_draft_fails(self):
        user = create_user(504)

        # 1. создаём draft
        test = self.create_test(user)

        image = self.create_image(test)

        # 2. переводим в active
        test.status = TestModel.Status.ACTIVE
        test.save()

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-detail", kwargs={
            "test_id": test.id,
            "image_id": image.id
        })

        response = client.patch(
            url,
            data={"position": 2},
            format="multipart",
        )

        debug_response(response)

        assert response.status_code == 400

    # 🗑 DELETE
    def test_delete_image(self):
        user = create_user(505)
        test = self.create_test(user)

        image = self.create_image(test)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-detail", kwargs={
            "test_id": test.id,
            "image_id": image.id
        })

        response = client.delete(url)

        debug_response(response)

        assert response.status_code == 204
        assert not Image.objects.filter(id=image.id).exists()

    # 🔁 REORDER
    def test_reorder_images(self):
        user = create_user(506)
        test = self.create_test(user)

        img1 = Image.objects.create(test=test, position=1, image=self.create_file())
        img2 = Image.objects.create(test=test, position=2, image=self.create_file())

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-reorder", kwargs={"test_id": test.id})

        response = client.post(
            url,
            data={
                "items": [
                    {"id": img1.id, "position": 2},
                    {"id": img2.id, "position": 1},
                ]
            },
            format="json",
        )

        debug_response(response)

        assert response.status_code == 200

        img1.refresh_from_db()
        img2.refresh_from_db()

        assert img1.position == 2
        assert img2.position == 1

    # ❌ REORDER дубликаты
    def test_reorder_duplicate_positions_fails(self):
        user = create_user(507)
        test = self.create_test(user)

        img1 = Image.objects.create(test=test, position=1, image=self.create_file())
        img2 = Image.objects.create(test=test, position=2, image=self.create_file())

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("image-reorder", kwargs={"test_id": test.id})

        response = client.post(
            url,
            data={
                "items": [
                    {"id": img1.id, "position": 1},
                    {"id": img2.id, "position": 1},
                ]
            },
            format="json",
        )

        debug_response(response)

        assert response.status_code == 400