import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_login_success(client):
    user = User.objects.create_user(email="test@example.com", password="123456")
    user.is_verified = True
    user.save()

    response = client.post(reverse("login"), {
        "email": "test@example.com",
        "password": "123456"
    })

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_wrong_password(client):
    user = User.objects.create_user(email="test@example.com", password="123456")
    user.is_verified = True
    user.save()

    response = client.post(reverse("login"), {
        "email": "test@example.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 401


@pytest.mark.django_db
def test_login_not_verified(client):
    User.objects.create_user(email="test@example.com", password="123456")

    response = client.post(reverse("login"), {
        "email": "test@example.com",
        "password": "123456"
    })

    assert response.status_code == 400
    assert "Email не подтверждён" in str(response.data)


@pytest.mark.django_db
def test_me_get_authorized(client):
    user = User.objects.create_user(
        email="test@example.com",
        password="123456",
    )
    user.is_verified = True
    user.save()

    login_response = client.post(reverse("login"), {
        "email": "test@example.com",
        "password": "123456"
    })

    access = login_response.data["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get(reverse("me"))

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 200
    assert response.data["email"] == "test@example.com"


@pytest.mark.django_db
def test_logout_success(client):
    user = User.objects.create_user(
        email="test@example.com",
        password="123456",
    )
    user.is_verified = True
    user.save()

    login_response = client.post(reverse("login"), {
        "email": "test@example.com",
        "password": "123456"
    })

    access = login_response.data["access"]
    refresh = login_response.data["refresh"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(reverse("logout"), {
        "refresh": refresh
    })

    assert response.status_code == 204