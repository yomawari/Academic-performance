from __future__ import annotations

import sqlite3

from ..errors import APIError
from ..security import hash_password

TEACHER_SELECT = """
    SELECT t.id,
           t.user_id,
           u.username,
           u.full_name,
           t.department,
           t.position,
           (SELECT COUNT(*) FROM teacher_subject ts WHERE ts.teacher_id = t.id) AS subject_count,
           u.is_active
      FROM teachers t
      JOIN users u ON u.id = t.user_id
"""


def list_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(TEACHER_SELECT + " ORDER BY u.full_name").fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, teacher_id: int) -> dict:
    row = conn.execute(TEACHER_SELECT + " WHERE t.id = ?", (teacher_id,)).fetchone()
    if row is None:
        raise APIError(404, "Преподаватель не найден", "not_found")
    return dict(row)


def create(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    full_name: str,
    department: str,
    position: str,
) -> dict:
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, 'teacher')
            """,
            (username, hash_password(password), full_name),
        )
        user_id = int(cur.lastrowid)
        cur = conn.execute(
            "INSERT INTO teachers (user_id, department, position) VALUES (?, ?, ?)",
            (user_id, department, position),
        )
    except sqlite3.IntegrityError as exc:
        raise APIError(409, "Пользователь с таким логином уже существует", "duplicate") from exc
    return get(conn, int(cur.lastrowid))


def update(conn: sqlite3.Connection, teacher_id: int, fields: dict) -> dict:
    teacher = get(conn, teacher_id)

    user_changes: dict[str, object] = {}
    if "full_name" in fields:
        user_changes["full_name"] = fields["full_name"]
    if "is_active" in fields:
        user_changes["is_active"] = int(bool(fields["is_active"]))
    if user_changes:
        assignments = ", ".join(f"{key} = ?" for key in user_changes)
        conn.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*user_changes.values(), teacher["user_id"]),
        )

    allowed = {"department", "position"}
    changes = {key: value for key, value in fields.items() if key in allowed}
    if changes:
        assignments = ", ".join(f"{key} = ?" for key in changes)
        conn.execute(
            f"UPDATE teachers SET {assignments} WHERE id = ?",
            (*changes.values(), teacher_id),
        )
    return get(conn, teacher_id)


def delete(conn: sqlite3.Connection, teacher_id: int) -> None:
    teacher = get(conn, teacher_id)
    conn.execute("DELETE FROM users WHERE id = ?", (teacher["user_id"],))
