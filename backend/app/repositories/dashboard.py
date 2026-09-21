from __future__ import annotations

import sqlite3


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int | float | None:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def _global_dashboard(conn: sqlite3.Connection) -> dict:
    average = _scalar(conn, "SELECT ROUND(AVG(value), 2) FROM grades")
    return {
        "students": int(_scalar(conn, "SELECT COUNT(*) FROM students") or 0),
        "groups": int(_scalar(conn, "SELECT COUNT(*) FROM groups") or 0),
        "teachers": int(_scalar(conn, "SELECT COUNT(*) FROM teachers") or 0),
        "subjects": int(_scalar(conn, "SELECT COUNT(*) FROM subjects") or 0),
        "lessons": int(_scalar(conn, "SELECT COUNT(*) FROM lessons") or 0),
        "grades": int(_scalar(conn, "SELECT COUNT(*) FROM grades") or 0),
        "average_grade": float(average) if average is not None else None,
    }


def _student_dashboard(conn: sqlite3.Connection, user_id: int) -> dict:
    student = conn.execute(
        "SELECT id, group_id FROM students WHERE user_id = ?", (user_id,)
    ).fetchone()
    if student is None:
        return {
            "students": 0,
            "groups": 0,
            "teachers": 0,
            "subjects": 0,
            "lessons": 0,
            "grades": 0,
            "average_grade": None,
        }

    student_id = int(student["id"])
    group_id = student["group_id"]
    average = _scalar(
        conn, "SELECT ROUND(AVG(value), 2) FROM grades WHERE student_id = ?", (student_id,)
    )
    if group_id is None:
        return {
            "students": 1,
            "groups": 0,
            "teachers": 0,
            "subjects": 0,
            "lessons": 0,
            "grades": int(
                _scalar(conn, "SELECT COUNT(*) FROM grades WHERE student_id = ?", (student_id,))
                or 0
            ),
            "average_grade": float(average) if average is not None else None,
        }

    return {
        "students": 1,
        "groups": 1,
        "teachers": int(
            _scalar(
                conn,
                "SELECT COUNT(DISTINCT teacher_id) FROM lessons WHERE group_id = ?",
                (group_id,),
            )
            or 0
        ),
        "subjects": int(
            _scalar(
                conn,
                "SELECT COUNT(DISTINCT subject_id) FROM lessons WHERE group_id = ?",
                (group_id,),
            )
            or 0
        ),
        "lessons": int(
            _scalar(conn, "SELECT COUNT(*) FROM lessons WHERE group_id = ?", (group_id,)) or 0
        ),
        "grades": int(
            _scalar(conn, "SELECT COUNT(*) FROM grades WHERE student_id = ?", (student_id,)) or 0
        ),
        "average_grade": float(average) if average is not None else None,
    }


def get_dashboard(conn: sqlite3.Connection, *, role: str, user_id: int) -> dict:
    if role == "student":
        return _student_dashboard(conn, user_id)
    return _global_dashboard(conn)
