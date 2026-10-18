from __future__ import annotations

import sqlite3

from ..errors import APIError

LESSON_SELECT = """
    SELECT l.id,
           l.subject_id,
           s.title AS subject_title,
           l.group_id,
           g.name AS group_name,
           l.teacher_id,
           tu.full_name AS teacher_name,
           l.lesson_date,
           l.topic,
           l.homework,
           l.lesson_type,
           (SELECT COUNT(*) FROM grades gr WHERE gr.lesson_id = l.id) AS grades_count
      FROM lessons l
      JOIN subjects s ON s.id = l.subject_id
      JOIN groups g ON g.id = l.group_id
      LEFT JOIN teachers t ON t.id = l.teacher_id
      LEFT JOIN users tu ON tu.id = t.user_id
"""


def list_all(
    conn: sqlite3.Connection,
    *,
    group_id: int | None = None,
    subject_id: int | None = None,
    only_user_id: int | None = None,
) -> list[dict]:
    conditions: list[str] = []
    params: list[object] = []
    if group_id is not None:
        conditions.append("l.group_id = ?")
        params.append(group_id)
    if subject_id is not None:
        conditions.append("l.subject_id = ?")
        params.append(subject_id)
    if only_user_id is not None:
        conditions.append("l.group_id = (SELECT group_id FROM students WHERE user_id = ?)")
        params.append(only_user_id)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        LESSON_SELECT + where + " ORDER BY l.lesson_date DESC, l.id DESC", params
    ).fetchall()
    return [dict(row) for row in rows]


def get(conn: sqlite3.Connection, lesson_id: int) -> dict:
    row = conn.execute(LESSON_SELECT + " WHERE l.id = ?", (lesson_id,)).fetchone()
    if row is None:
        raise APIError(404, "Занятие не найдено", "not_found")
    return dict(row)


def subject_teacher(conn: sqlite3.Connection, subject_id: int) -> int | None:
    row = conn.execute("SELECT teacher_id FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    if row is None:
        raise APIError(404, "Дисциплина не найдена", "not_found")
    return row["teacher_id"]


def create(conn: sqlite3.Connection, values: dict) -> dict:
    try:
        cursor = conn.execute(
            """
            INSERT INTO lessons
                (subject_id, group_id, teacher_id, lesson_date, topic, homework, lesson_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["subject_id"],
                values["group_id"],
                values.get("teacher_id"),
                values["lesson_date"],
                values["topic"],
                values.get("homework") or "",
                values.get("lesson_type") or "practice",
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise APIError(409, "Не удалось создать занятие: проверьте группу и дисциплину", "conflict") from exc
    return get(conn, int(cursor.lastrowid))


def update(conn: sqlite3.Connection, lesson_id: int, values: dict) -> dict:
    get(conn, lesson_id)
    allowed = {"subject_id", "group_id", "teacher_id", "lesson_date", "topic", "homework", "lesson_type"}
    changes = {key: value for key, value in values.items() if key in allowed}
    if changes:
        assignments = ", ".join(f"{key} = ?" for key in changes)
        try:
            conn.execute(
                f"UPDATE lessons SET {assignments} WHERE id = ?",
                (*changes.values(), lesson_id),
            )
        except sqlite3.IntegrityError as exc:
            raise APIError(409, "Не удалось обновить занятие", "conflict") from exc
    return get(conn, lesson_id)


def delete(conn: sqlite3.Connection, lesson_id: int) -> None:
    get(conn, lesson_id)
    conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
