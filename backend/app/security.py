"""Пароли и сессионные токены.

Пароли хранятся в виде scrypt-хэша с индивидуальной солью. Токен —
подписанный HMAC-SHA256 компактный JSON, который передаётся в
HttpOnly-cookie. Сторонние библиотеки не используются.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from . import config

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
_ALGORITHM = "scrypt"


class TokenError(ValueError):
    """Токен отсутствует, повреждён или истёк."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return "$".join(
        [
            _ALGORITHM,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _b64encode(salt),
            _b64encode(digest),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Хэш-«пустышка» нужен, чтобы время ответа при несуществующем логине
# не отличалось от времени ответа при неверном пароле.
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


def create_access_token(
    user_id: int,
    role: str,
    *,
    ttl: int = config.TOKEN_TTL_SECONDS,
    secret: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + ttl,
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signature = hmac.new(
        (secret or config.secret_key()).encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{body}.{_b64encode(signature)}"


def decode_access_token(token: str, *, secret: str | None = None) -> dict[str, Any]:
    try:
        body, signature_b64 = token.split(".", 1)
        expected = hmac.new(
            (secret or config.secret_key()).encode("utf-8"),
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual = _b64decode(signature_b64)
    except (ValueError, UnicodeError) as exc:
        raise TokenError("Некорректный токен") from exc

    if not hmac.compare_digest(actual, expected):
        raise TokenError("Подпись токена неверна")

    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, UnicodeError) as exc:
        raise TokenError("Некорректное содержимое токена") from exc

    if not isinstance(payload, dict) or "sub" not in payload:
        raise TokenError("Некорректное содержимое токена")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Срок действия токена истёк")
    return payload
