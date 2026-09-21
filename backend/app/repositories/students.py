from __future__ import annotations

import sqlite3

from ..errors import APIError
from ..security import hash_password

STUDENT_SELECT = """
    SELECT st.id,
           st.user_id,
           u.username,
           u.full_name,
           st.group_id,
           g.name AS group_name,
           st.record_book_no,
           st.email,
           st.phone,
           u.is_active
      FROM students st
      JOIN users u ON u.id = st.user_id
      LEFT JOIN groups g ON g.id = st.group_id
"""


def list_all(
    conn: sqlite3.Connection,
    *,
    group_id: int | None = None,
    search: str | None = None,
    only_user_id: int | None = None,
) -> list[dict]:
    conditions: list[str] = []
    params: list[object] = []
    if group_id is not None:
        conditions.append("st.group_id = ?")
        params.append(group_id)
    if search:
        conditions.append("(u.full_name LIKE ? OR st.record_book_no LIKE ?)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern])
    if only_user_id is not None:
        conditions.append("st.user_id = ?")
        params.append(only_user_id)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(STUDENT_SELECT + where + " ORDER BY u.full_name", params).fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, student_id: int) -> dict:
    row = conn.execute(STUDENT_SELECT + " WHERE st.id = ?", (student_id,)).fetchone()
    if row is None:
        raise APIError(404, "Студент не найден", "not_found")
    return dict(row)


def _validate_group(conn: sqlite3.Connection, group_id: int | None) -> None:
    if group_id is None:
        return
    if conn.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,)).fetchone() is None:
        raise APIError(404, "Учебная группа не найдена", "not_found")


def create(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    full_name: str,
    group_id: int | None,
    record_book_no: str,
    email: str | None,
    phone: str | None,
) -> dict:
    _validate_group(conn, group_id)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, 'student')
            """,
            (username, hash_password(password), full_name),
        )
        user_id = int(cur.lastrowid)
        cur = conn.execute(
            """
            INSERT INTO students (user_id, group_id, record_book_no, email, phone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, group_id, record_book_no, email, phone),
        )
    except sqlite3.IntegrityError as exc:
        raise APIError(
            409,
            "Логин или номер зачётной книжки уже используется",
            "duplicate",
        ) from exc
    return get(conn, int(cur.lastrowid))


def update(conn: sqlite3.Connection, student_id: int, fields: dict) -> dict:
    student = get(conn, student_id)
    if "group_id" in fields:
        _validate_group(conn, fields["group_id"])

    user_changes: dict[str, object] = {}
    if "full_name" in fields:
        user_changes["full_name"] = fields["full_name"]
    if "is_active" in fields:
        user_changes["is_active"] = int(bool(fields["is_active"]))
    if user_changes:
        assignments = ", ".join(f"{key} = ?" for key in user_changes)
        conn.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*user_changes.values(), student["user_id"]),
        )

    allowed = {"group_id", "record_book_no", "email", "phone"}
    changes = {key: value for key, value in fields.items() if key in allowed}
    if changes:
        assignments = ", ".join(f"{key} = ?" for key in changes)
        try:
            conn.execute(
                f"UPDATE students SET {assignments} WHERE id = ?",
                (*changes.values(), student_id),
            )
        except sqlite3.IntegrityError as exc:
            raise APIError(409, "Номер зачётной книжки уже используется", "duplicate") from exc
    return get(conn, student_id)


def delete(conn: sqlite3.Connection, student_id: int) -> None:
    student = get(conn, student_id)
    conn.execute("DELETE FROM users WHERE id = ?", (student["user_id"],))
