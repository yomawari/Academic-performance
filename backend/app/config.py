"""Конфигурация приложения.

Все пути и секреты можно переопределить переменными окружения — это
используется в тестах и при развёртывании.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
API_DIR = BASE_DIR / "api"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.sql"

APP_NAME = "Учёт успеваемости"
APP_VERSION = "0.1.0"
API_PREFIX = "/api"
COOKIE_NAME = "access_token"
TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 часов


def data_dir() -> Path:
    return Path(os.getenv("APP_DATA_DIR", BASE_DIR / "backend" / "data"))


def db_path() -> Path:
    return Path(os.getenv("APP_DB_PATH", data_dir() / "academic.db"))


def secret_key() -> str:
    """Секрет подписи токенов.

    В учебном окружении секрет генерируется один раз и сохраняется в
    закрытом файле. В промышленной эксплуатации задаётся через APP_SECRET.
    """
    env_secret = os.getenv("APP_SECRET")
    if env_secret:
        return env_secret

    path = data_dir() / "secret.key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value
