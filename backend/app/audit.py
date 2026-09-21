"""Журнал действий пользователей."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def write_audit(
    conn: sqlite3.Connection,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity, entity_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            entity,
            entity_id,
            json.dumps(details, ensure_ascii=False) if details else None,
        ),
    )
