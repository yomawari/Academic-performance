"""Точка входа FastAPI-приложения «Учёт успеваемости»."""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import init_db, session
from .deps import require_admin
from .errors import APIError, api_error_handler
from .routers import auth, dashboard, groups, students, subjects, teachers


def ensure_database() -> None:
    if not config.db_path().exists():
        init_db()
    with session() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0 and os.getenv("APP_AUTO_SEED", "1") != "0":
        from backend import seed

        seed.seed_data()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database()
    yield


app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description=(
        "Серверная часть информационной системы «Учёт успеваемости». "
        "Первичным контрактом является api/openapi.yaml."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_exception_handler(APIError, api_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first.get("loc", [])[1:])
    message = first.get("msg", "Некорректные данные")
    detail = f"Некорректное поле «{location}»: {message}" if location else message
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "code": "validation_error"},
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'",
    )
    return response


app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(subjects.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["Auth"])
def health() -> dict:
    return {"status": "ok", "version": config.APP_VERSION}


@app.get("/api/openapi.yaml", include_in_schema=False)
def openapi_contract() -> FileResponse:
    """Первичный контракт в формате YAML."""
    return FileResponse(
        config.API_DIR / "openapi.yaml",
        media_type="application/yaml",
        filename="openapi.yaml",
    )


@app.get("/api/audit", include_in_schema=False)
def audit_tail(
    limit: int = 20,
    _user: dict = Depends(require_admin),
) -> list[dict]:
    """Последние действия (только для администратора, вне публичного контракта)."""
    limit = max(1, min(limit, 100))
    with session() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.action, a.entity, a.entity_id, a.details, a.created_at,
                   u.full_name AS user_name
              FROM audit_log a
              LEFT JOIN users u ON u.id = a.user_id
             ORDER BY a.id DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


if config.FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "img" / "favicon.svg", media_type="image/svg+xml")
