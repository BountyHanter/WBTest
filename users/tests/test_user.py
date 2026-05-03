import json
from unittest.mock import patch

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
@pytest.mark.django_db
def test_password_reset_email_sent(monkeypatch, client):
    user = User.objects.create_user(email="test@example.com", password="123456")

    called = {}

    def fake_send(u):
        called["user"] = u

    monkeypatch.setattr(
        "users.views.reset_password.send_password_reset",
        fake_send
    )

    response = client.post(reverse("password-reset"), {
        "email": "test@example.com"
    })

    if pytest.DEBUG:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))

    assert response.status_code == 200
    assert called["user"] == user


@pytest.mark.django_db
def test_password_reset_user_not_found(monkeypatch, client):
    called = False

    def fake_send(u):
        nonlocal called
        called = True

    monkeypatch.setattr(
        "users.views.reset_password.send_password_reset",
        fake_send
    )

    response = client.post(reverse("password-reset"), {
        "email": "unknown@example.com"
    })

    if pytest.DEBUG:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))

    assert response.status_code == 200
    assert called is False


@pytest.mark.django_db
def test_password_reset_confirm_success(monkeypatch, client):
    user = User.objects.create_user(email="test@example.com", password="123456")

    monkeypatch.setattr(
        "users.views.reset_password.check_verification_token",
        lambda user, token: True
    )

    response = client.post(reverse("password-reset-confirm"), {
        "user_id": user.id,
        "token": "valid",
        "password": "newpassword"
    })

    if pytest.DEBUG:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))

    user.refresh_from_db()

    assert response.status_code == 200
    assert user.check_password("newpassword")


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token(monkeypatch, client):
    user = User.objects.create_user(email="test@example.com", password="123456")

    monkeypatch.setattr(
        "users.views.reset_password.check_verification_token",
        lambda user, token: False
    )

    response = client.post(reverse("password-reset-confirm"), {
        "user_id": user.id,
        "token": "bad",
        "password": "newpassword"
    })

    if pytest.DEBUG:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))

    assert response.status_code == 400


@pytest.mark.django_db
def test_password_reset_confirm_user_not_found(client):
    response = client.post(reverse("password-reset-confirm"), {
        "user_id": 999,
        "token": "token",
        "password": "newpassword"
    })

    if pytest.DEBUG:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))

    assert response.status_code == 404