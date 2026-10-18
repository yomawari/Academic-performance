from __future__ import annotations

import sqlite3

from ..errors import APIError
from . import lessons

ENTRY_SELECT = """
    SELECT st.id AS student_id,
           u.full_name,
           st.record_book_no,
           gr.id AS grade_id,
           gr.value AS grade_value,
           COALESCE(gr.comment, '') AS grade_comment,
           a.status AS attendance_status,
           COALESCE(a.comment, '') AS attendance_comment
      FROM students st
      JOIN users u ON u.id = st.user_id
      LEFT JOIN grades gr ON gr.student_id = st.id AND gr.lesson_id = ?
      LEFT JOIN attendance a ON a.student_id = st.id AND a.lesson_id = ?
     WHERE st.group_id = ?
"""


def _entry(conn: sqlite3.Connection, lesson_id: int, student_id: int) -> dict:
    lesson = lessons.get(conn, lesson_id)
    row = conn.execute(
        ENTRY_SELECT + " AND st.id = ?",
        (lesson_id, lesson_id, lesson["group_id"], student_id),
    ).fetchone()
    if row is None:
        raise APIError(404, "Студент не найден в группе занятия", "not_found")
    return dict(row)


def get_journal(conn: sqlite3.Connection, lesson_id: int) -> dict:
    lesson = lessons.get(conn, lesson_id)
    rows = conn.execute(
        ENTRY_SELECT + " ORDER BY u.full_name",
        (lesson_id, lesson_id, lesson["group_id"]),
    ).fetchall()
    return {"lesson": lesson, "entries": [dict(row) for row in rows]}


def _set_grade(
    conn: sqlite3.Connection,
    *,
    lesson_id: int,
    student_id: int,
    value: int | None,
    comment: str,
    user_id: int,
) -> None:
    if value is None:
        conn.execute(
            "DELETE FROM grades WHERE student_id = ? AND lesson_id = ?",
            (student_id, lesson_id),
        )
        return
    conn.execute(
        """
        INSERT INTO grades (student_id, lesson_id, value, comment, created_by)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (student_id, lesson_id) DO UPDATE SET
            value = excluded.value,
            comment = excluded.comment,
            updated_at = datetime('now')
        """,
        (student_id, lesson_id, value, comment, user_id),
    )


def _set_attendance(
    conn: sqlite3.Connection,
    *,
    lesson_id: int,
    student_id: int,
    status: str | None,
    comment: str,
) -> None:
    if status is None:
        conn.execute(
            "DELETE FROM attendance WHERE student_id = ? AND lesson_id = ?",
            (student_id, lesson_id),
        )
        return
    conn.execute(
        """
        INSERT INTO attendance (student_id, lesson_id, status, comment)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (student_id, lesson_id) DO UPDATE SET
            status = excluded.status,
            comment = excluded.comment
        """,
        (student_id, lesson_id, status, comment),
    )


def save_entry(
    conn: sqlite3.Connection,
    *,
    lesson_id: int,
    student_id: int,
    values: dict,
    user_id: int,
) -> dict:
    lesson = lessons.get(conn, lesson_id)
    student = conn.execute(
        "SELECT id FROM students WHERE id = ? AND group_id = ?",
        (student_id, lesson["group_id"]),
    ).fetchone()
    if student is None:
        raise APIError(404, "Студент не найден в группе занятия", "not_found")

    if "grade_value" in values:
        grade_value = values.get("grade_value")
        _set_grade(
            conn,
            lesson_id=lesson_id,
            student_id=student_id,
            value=int(grade_value) if grade_value is not None else None,
            comment=values.get("grade_comment") or "",
            user_id=user_id,
        )

    if "attendance_status" in values:
        status = values.get("attendance_status")
        _set_attendance(
            conn,
            lesson_id=lesson_id,
            student_id=student_id,
            status=str(status) if status is not None else None,
            comment=values.get("attendance_comment") or "",
        )

    return _entry(conn, lesson_id, student_id)
