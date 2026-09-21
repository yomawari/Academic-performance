from __future__ import annotations


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_current_user(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["username"] == "admin"
    assert "password_hash" not in body
    assert "access_token" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["full_name"] == "Администратор системы"


def test_login_is_case_insensitive_for_username(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "ADMIN", "password": "admin123"},
    )
    assert response.status_code == 200


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_logout_clears_session(admin_client):
    response = admin_client.post("/api/auth/logout")
    assert response.status_code == 204
    assert admin_client.get("/api/auth/me").status_code == 401


def test_inactive_account_cannot_login(admin_client):
    created = admin_client.post(
        "/api/students",
        json={
            "username": "inactive.user",
            "password": "secret123",
            "full_name": "Отключённый Пользователь",
            "record_book_no": "99-001",
        },
    )
    assert created.status_code == 201, created.text
    student_id = created.json()["id"]

    updated = admin_client.patch(
        f"/api/students/{student_id}",
        json={"is_active": False},
    )
    assert updated.status_code == 200

    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as anonymous:
        response = anonymous.post(
            "/api/auth/login",
            json={"username": "inactive.user", "password": "secret123"},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "account_disabled"

    admin_client.delete(f"/api/students/{student_id}")
