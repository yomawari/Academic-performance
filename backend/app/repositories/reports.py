from __future__ import annotations

import sqlite3

from ..errors import APIError
from . import students


def group_report(conn: sqlite3.Connection, group_id: int) -> dict:
    group = conn.execute("SELECT id, name FROM groups WHERE id = ?", (group_id,)).fetchone()
    if group is None:
        raise APIError(404, "Учебная группа не найдена", "not_found")

    rows = conn.execute(
        """
        SELECT st.id AS student_id,
               u.full_name,
               st.record_book_no,
               (SELECT ROUND(AVG(value), 2) FROM grades WHERE student_id = st.id) AS average_grade,
               (SELECT COUNT(*) FROM grades WHERE student_id = st.id) AS grades_count,
               (SELECT COUNT(*) FROM attendance
                 WHERE student_id = st.id AND status = 'absent') AS absences,
               (SELECT COUNT(*) FROM attendance
                 WHERE student_id = st.id AND status = 'late') AS lates
          FROM students st
          JOIN users u ON u.id = st.user_id
         WHERE st.group_id = ?
         ORDER BY u.full_name
        """,
        (group_id,),
    ).fetchall()

    return {
        "group_id": group["id"],
        "group_name": group["name"],
        "students": [dict(row) for row in rows],
    }


def student_report(conn: sqlite3.Connection, student_id: int) -> dict:
    student = students.get(conn, student_id)

    subjects = [
        dict(row)
        for row in conn.execute(
            """
            SELECT s.id AS subject_id,
                   s.title,
                   ROUND(AVG(gr.value), 2) AS average_grade,
                   COUNT(gr.id) AS grades_count
              FROM grades gr
              JOIN lessons l ON l.id = gr.lesson_id
              JOIN subjects s ON s.id = l.subject_id
             WHERE gr.student_id = ?
             GROUP BY s.id, s.title
             ORDER BY s.title
            """,
            (student_id,),
        ).fetchall()
    ]

    grades = [
        dict(row)
        for row in conn.execute(
            """
            SELECT gr.id,
                   l.lesson_date,
                   s.title AS subject_title,
                   gr.value,
                   gr.comment
              FROM grades gr
              JOIN lessons l ON l.id = gr.lesson_id
              JOIN subjects s ON s.id = l.subject_id
             WHERE gr.student_id = ?
             ORDER BY l.lesson_date DESC, gr.id DESC
             LIMIT 30
            """,
            (student_id,),
        ).fetchall()
    ]

    return {"student": student, "subjects": subjects, "grades": grades}
