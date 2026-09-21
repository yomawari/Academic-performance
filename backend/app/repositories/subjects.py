from __future__ import annotations

import sqlite3

from ..errors import APIError

SUBJECT_SELECT = """
    SELECT s.id,
           s.code,
           s.title,
           s.description,
           s.hours,
           s.teacher_id,
           u.full_name AS teacher_name,
           (SELECT COUNT(*) FROM group_subject gs WHERE gs.subject_id = s.id) AS group_count,
           (SELECT COUNT(*) FROM teacher_subject ts WHERE ts.subject_id = s.id) AS teacher_count
      FROM subjects s
      LEFT JOIN teachers t ON t.id = s.teacher_id
      LEFT JOIN users u ON u.id = t.user_id
"""


def list_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(SUBJECT_SELECT + " ORDER BY s.title").fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, subject_id: int) -> dict:
    row = conn.execute(SUBJECT_SELECT + " WHERE s.id = ?", (subject_id,)).fetchone()
    if row is None:
        raise APIError(404, "Дисциплина не найдена", "not_found")
    return dict(row)


def _validate_teacher(conn: sqlite3.Connection, teacher_id: int | None) -> None:
    if teacher_id is None:
        return
    if conn.execute("SELECT 1 FROM teachers WHERE id = ?", (teacher_id,)).fetchone() is None:
        raise APIError(404, "Преподаватель не найден", "not_found")


def _link_teacher(conn: sqlite3.Connection, subject_id: int, teacher_id: int | None) -> None:
    if teacher_id is None:
        return
    conn.execute(
        "INSERT OR IGNORE INTO teacher_subject (teacher_id, subject_id) VALUES (?, ?)",
        (teacher_id, subject_id),
    )


def create(
    conn: sqlite3.Connection,
    *,
    code: str,
    title: str,
    description: str,
    hours: int,
    teacher_id: int | None,
) -> dict:
    _validate_teacher(conn, teacher_id)
    try:
        cur = conn.execute(
            """
            INSERT INTO subjects (code, title, description, hours, teacher_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, title, description, hours, teacher_id),
        )
    except sqlite3.IntegrityError as exc:
        raise APIError(409, "Дисциплина с таким кодом уже существует", "duplicate") from exc
    subject_id = int(cur.lastrowid)
    _link_teacher(conn, subject_id, teacher_id)
    return get(conn, subject_id)


def update(conn: sqlite3.Connection, subject_id: int, fields: dict) -> dict:
    get(conn, subject_id)
    if "teacher_id" in fields:
        _validate_teacher(conn, fields["teacher_id"])
    allowed = {"code", "title", "description", "hours", "teacher_id"}
    changes = {key: value for key, value in fields.items() if key in allowed}
    if changes:
        assignments = ", ".join(f"{key} = ?" for key in changes)
        try:
            conn.execute(
                f"UPDATE subjects SET {assignments} WHERE id = ?",
                (*changes.values(), subject_id),
            )
        except sqlite3.IntegrityError as exc:
            raise APIError(409, "Дисциплина с таким кодом уже существует", "duplicate") from exc
    if "teacher_id" in fields:
        _link_teacher(conn, subject_id, fields["teacher_id"])
    return get(conn, subject_id)


def delete(conn: sqlite3.Connection, subject_id: int) -> None:
    get(conn, subject_id)
    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
