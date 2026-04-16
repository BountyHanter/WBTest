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
