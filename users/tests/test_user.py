import json

import pytest
from django.contrib.auth import get_user_model
from pygments.lexers import data

User = get_user_model()


@pytest.mark.django_db
def test_register_success(client):
    response = client.post("/api/v1/users/register/", {
        "email": "test@example.com",
        "password": "strongpassword123"
    })
    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 201
    assert "access" in response.data
    assert "refresh" in response.data

    assert User.objects.filter(email="test@example.com").exists()


@pytest.mark.django_db
def test_register_duplicate_email(client):
    User.objects.create_user(email="test@example.com", password="123456")

    response = client.post("/api/v1/users/register/", {
        "email": "test@example.com",
        "password": "123456"
    })
    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 400


@pytest.mark.django_db
def test_login_success(client):
    User.objects.create_user(email="test@example.com", password="123456")

    response = client.post("/api/v1/users/login/", {
        "email": "test@example.com",
        "password": "123456"
    })
    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_wrong_password(client):
    User.objects.create_user(email="test@example.com", password="123456")

    response = client.post("/api/v1/users/login/", {
        "email": "test@example.com",
        "password": "wrongpassword"
    })

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))

    assert response.status_code == 400

@pytest.mark.django_db
def test_me_get_unauthorized(client):
    response = client.get("/api/v1/users/me/")

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(f"{response.status_code}, {data}", ensure_ascii=False, indent=4))


    assert response.status_code == 401


@pytest.mark.django_db
def test_me_get_authorized(client):
    User.objects.create_user(
        email="test@example.com",
        password="123456",
        wb_token="test_token"
    )

    # логинимся
    login_response = client.post("/api/v1/users/login/", {
        "email": "test@example.com",
        "password": "123456"
    })

    access = login_response.data["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/users/me/")

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 200
    assert response.data["email"] == "test@example.com"
    assert response.data["wb_token"] == "test_token"


@pytest.mark.django_db
def test_me_patch_update_token(client):
    user = User.objects.create_user(
        email="test@example.com",
        password="123456",
        wb_token=None
    )

    login_response = client.post("/api/v1/users/login/", {
        "email": "test@example.com",
        "password": "123456"
    })

    access = login_response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch("/api/v1/users/me/", {
        "wb_token": "new_token"
    })

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))

    assert response.status_code == 200

    user.refresh_from_db()
    assert user.wb_token == "new_token"


@pytest.mark.django_db
def test_me_patch_empty(client):
    user = User.objects.create_user(
        email="test@example.com",
        password="123456",
        wb_token="old_token"
    )

    login_response = client.post("/api/v1/users/login/", {
        "email": "test@example.com",
        "password": "123456"
    })

    access = login_response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.patch("/api/v1/users/me/", {})

    if pytest.DEBUG:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=4))


    assert response.status_code == 200

    user.refresh_from_db()
    assert user.wb_token == "old_token"