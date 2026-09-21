from __future__ import annotations


def test_sql_injection_in_login_is_rejected(client):
    for payload in ["' OR 1=1 --", "admin'--", "'; DROP TABLE users; --"]:
        response = client.post(
            "/api/auth/login",
            json={"username": payload, "password": payload},
        )
        assert response.status_code == 401

    # Таблица users не повреждена — вход с корректными данными работает.
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200


def test_sql_injection_in_search_is_safe(admin_client):
    response = admin_client.get(
        "/api/students",
        params={"search": "%' OR '1'='1' --"},
    )
    assert response.status_code == 200
    assert response.json() == []

    # Таблица по-прежнему доступна и содержит данные.
    assert len(admin_client.get("/api/students").json()) >= 12


def test_tampered_token_is_rejected(client):
    client.cookies.set("access_token", "eyJzdWIiOjF9.invalid-signature")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_session_cookie_is_httponly(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_security_headers_present(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_password_hash_is_not_exposed(admin_client):
    for path in ("/api/students", "/api/teachers"):
        response = admin_client.get(path)
        assert response.status_code == 200
        assert all("password_hash" not in item for item in response.json())

    me = admin_client.get("/api/auth/me")
    assert me.status_code == 200
    assert "password_hash" not in me.json()
