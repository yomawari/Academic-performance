from __future__ import annotations

import sqlite3

from ..errors import APIError

GROUP_SELECT = """
    SELECT g.id,
           g.name,
           g.course,
           g.curator_id,
           u.full_name AS curator_name,
           (SELECT COUNT(*) FROM students s WHERE s.group_id = g.id) AS student_count
      FROM groups g
      LEFT JOIN teachers t ON t.id = g.curator_id
      LEFT JOIN users u ON u.id = t.user_id
"""


def list_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(GROUP_SELECT + " ORDER BY g.course, g.name").fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, group_id: int) -> dict:
    row = conn.execute(GROUP_SELECT + " WHERE g.id = ?", (group_id,)).fetchone()
    if row is None:
        raise APIError(404, "Учебная группа не найдена", "not_found")
    return dict(row)


def _validate_curator(conn: sqlite3.Connection, curator_id: int | None) -> None:
    if curator_id is None:
        return
    row = conn.execute("SELECT 1 FROM teachers WHERE id = ?", (curator_id,)).fetchone()
    if row is None:
        raise APIError(404, "Преподаватель-куратор не найден", "not_found")


def create(conn: sqlite3.Connection, *, name: str, course: int, curator_id: int | None) -> dict:
    _validate_curator(conn, curator_id)
    try:
        cur = conn.execute(
            "INSERT INTO groups (name, course, curator_id) VALUES (?, ?, ?)",
            (name, course, curator_id),
        )
    except sqlite3.IntegrityError as exc:
        raise APIError(409, "Группа с таким названием уже существует", "duplicate") from exc
    return get(conn, int(cur.lastrowid))


def update(conn: sqlite3.Connection, group_id: int, fields: dict) -> dict:
    get(conn, group_id)
    allowed = {"name", "course", "curator_id"}
    changes = {key: value for key, value in fields.items() if key in allowed}
    if "curator_id" in changes:
        _validate_curator(conn, changes["curator_id"])
    if changes:
        assignments = ", ".join(f"{key} = ?" for key in changes)
        try:
            conn.execute(
                f"UPDATE groups SET {assignments} WHERE id = ?",
                (*changes.values(), group_id),
            )
        except sqlite3.IntegrityError as exc:
            raise APIError(409, "Группа с таким названием уже существует", "duplicate") from exc
    return get(conn, group_id)


def delete(conn: sqlite3.Connection, group_id: int) -> None:
    get(conn, group_id)
    conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
