from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepared_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    data_dir = tmp_path_factory.mktemp("academic-data")
    os.environ["APP_DB_PATH"] = str(data_dir / "test.db")
    os.environ["APP_DATA_DIR"] = str(data_dir)
    os.environ["APP_SECRET"] = "test-secret-key-for-pytest"
    os.environ["APP_AUTO_SEED"] = "0"

    from backend.seed import seed_data

    seed_data(force=True)
    return data_dir / "test.db"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as test_client:
        yield test_client


def _login(client, username: str, password: str):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def admin_client(client):
    _login(client, "admin", "admin123")
    return client


@pytest.fixture()
def teacher_client(client):
    _login(client, "teacher", "teacher123")
    return client


@pytest.fixture()
def student_client(client):
    _login(client, "student", "student123")
    return client
