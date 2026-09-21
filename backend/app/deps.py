"""Зависимости FastAPI: текущий пользователь и проверка ролей."""

from __future__ import annotations

import sqlite3
from typing import Callable

from fastapi import Depends, Request

from . import config
from .db import get_db
from .errors import APIError
from .security import TokenError, decode_access_token


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(config.COOKIE_NAME)
    if token:
        return token
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def get_current_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    token = _extract_token(request)
    if not token:
        raise APIError(401, "Требуется авторизация", "unauthorized")

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise APIError(401, str(exc), "invalid_token") from exc

    row = conn.execute(
        """
        SELECT id, username, full_name, role, is_active,
               created_at || 'Z' AS created_at,
               CASE WHEN last_login_at IS NOT NULL THEN last_login_at || 'Z' END AS last_login_at
          FROM users
         WHERE id = ? AND is_active = 1
        """,
        (payload["sub"],),
    ).fetchone()
    if row is None:
        raise APIError(401, "Учётная запись не найдена или отключена", "unauthorized")
    return dict(row)


def require_roles(*roles: str) -> Callable:
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise APIError(403, "Недостаточно прав для выполнения операции", "forbidden")
        return user

    return dependency


require_admin = require_roles("admin")
require_staff = require_roles("admin", "teacher")
