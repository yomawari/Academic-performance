from __future__ import annotations

import sqlite3

USER_FIELDS = """
    id,
    username,
    full_name,
    role,
    is_active,
    created_at || 'Z' AS created_at,
    CASE WHEN last_login_at IS NOT NULL THEN last_login_at || 'Z' END AS last_login_at
"""


def get_by_username(conn: sqlite3.Connection, username: str) -> dict | None:
    row = conn.execute(
        f"SELECT {USER_FIELDS}, password_hash FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def touch_login(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,))
