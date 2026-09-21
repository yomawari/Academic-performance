from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, Depends, Request, Response, status

from .. import config
from ..audit import write_audit
from ..contract.models import LoginRequest, User
from ..db import get_db
from ..deps import get_current_user
from ..errors import APIError
from ..repositories import users as users_repo
from ..security import DUMMY_PASSWORD_HASH, create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=User)
def login(
    payload: LoginRequest,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    account = users_repo.get_by_username(conn, payload.username)
    stored_hash = account["password_hash"] if account else DUMMY_PASSWORD_HASH
    password_ok = verify_password(payload.password, stored_hash)

    if account is None or not password_ok:
        raise APIError(401, "Неверный логин или пароль", "invalid_credentials")
    if not account["is_active"]:
        raise APIError(403, "Учётная запись отключена", "account_disabled")

    token = create_access_token(account["id"], account["role"])
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=token,
        max_age=config.TOKEN_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=os.getenv("APP_COOKIE_SECURE", "0") == "1",
        path="/",
    )
    users_repo.touch_login(conn, account["id"])
    write_audit(conn, account["id"], "login", "user", account["id"])
    account.pop("password_hash", None)
    return account


@router.get("/me", response_model=User)
def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    response.delete_cookie(config.COOKIE_NAME, path="/")
    write_audit(conn, user["id"], "logout", "user", user["id"])
