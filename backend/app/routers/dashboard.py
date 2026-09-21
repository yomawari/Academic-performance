from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..contract.models import DashboardStats
from ..db import get_db
from ..deps import get_current_user
from ..repositories.dashboard import get_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return get_dashboard(conn, role=user["role"], user_id=user["id"])
