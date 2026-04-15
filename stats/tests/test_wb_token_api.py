import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from stats.models import WBToken
from stats.tests.utils.factories import (
    create_user,
    create_wb_token,
    create_test,
)


@pytest.mark.django_db
class TestWBTokenAPI:

    def test_list_returns_only_user_tokens(self):
        user = create_user(1)
        other_user = create_user(2)

        own_token_1 = create_wb_token(user=user, token="own_token_1")
        own_token_2 = create_wb_token(user=user, token="own_token_2")
        create_wb_token(user=other_user, token="foreign_token")

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-list")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        response_ids = {item["id"] for item in response.data}
        assert response_ids == {own_token_1.id, own_token_2.id}

    def test_create_token(self):
        user = create_user(3)

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-list")
        response = client.post(
            url,
            data={"token": "new_token_value"},
            format="json",
        )

        if pytest.DEBUG:
            data = response.json()
            print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

        assert response.status_code == status.HTTP_201_CREATED
        assert WBToken.objects.filter(
            user=user,
            token="new_token_value",
        ).exists()

    def test_retrieve_own_token(self):
        user = create_user(4)
        wb_token = create_wb_token(user=user, token="my_token")

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-detail", kwargs={"pk": wb_token.id})
        response = client.get(url)

        if pytest.DEBUG:
            data = response.json()
            print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == wb_token.id

    def test_retrieve_foreign_token_returns_404(self):
        user = create_user(5)
        other_user = create_user(6)
        foreign_token = create_wb_token(user=other_user, token="foreign_token")

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-detail", kwargs={"pk": foreign_token.id})
        response = client.get(url)

        if pytest.DEBUG:
            data = response.json()
            print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_own_token(self):
        user = create_user(7)
        wb_token = create_wb_token(user=user, token="old_token")

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-detail", kwargs={"pk": wb_token.id})
        response = client.patch(
            url,
            data={"token": "updated_token"},
            format="json",
        )

        if pytest.DEBUG:
            data = response.json()
            print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

        assert response.status_code == status.HTTP_200_OK

        wb_token.refresh_from_db()
        assert wb_token.token == "updated_token"

    def test_delete_used_token_returns_400(self):
        user = create_user(8)
        wb_token = create_wb_token(user=user, token="used_token")

        create_test(
            user=user,
            name="test_with_token",
            wb_token=wb_token,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("wb-token-detail", kwargs={"pk": wb_token.id})
        response = client.delete(url)

        if pytest.DEBUG:
            data = response.json()
            print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert WBToken.objects.filter(id=wb_token.id).exists()