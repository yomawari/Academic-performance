from __future__ import annotations

import csv
import io
import sqlite3

from fastapi import APIRouter, Depends, Response

from ..contract.models import GroupReport, StudentReport
from ..db import get_db
from ..deps import get_current_user, require_staff
from ..errors import APIError
from ..repositories import reports as repo
from ..repositories import students as students_repo

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/groups/{group_id}", response_model=GroupReport)
def get_group_report(
    group_id: int,
    _user: dict = Depends(require_staff),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return repo.group_report(conn, group_id)


@router.get("/groups/{group_id}/export")
def export_group_report(
    group_id: int,
    _user: dict = Depends(require_staff),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    report = repo.group_report(conn, group_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        ["ФИО", "Зачётная книжка", "Средний балл", "Оценок", "Пропусков", "Опозданий"]
    )
    for row in report["students"]:
        writer.writerow(
            [
                row["full_name"],
                row["record_book_no"],
                "" if row["average_grade"] is None else f"{row['average_grade']:.2f}",
                row["grades_count"],
                row["absences"],
                row["lates"],
            ]
        )
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="group_{group_id}_report.csv"'
        },
    )


@router.get("/students/{student_id}", response_model=StudentReport)
def get_student_report(
    student_id: int,
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    student = students_repo.get(conn, student_id)
    if user["role"] == "student" and student["user_id"] != user["id"]:
        raise APIError(403, "Можно просматривать только свою успеваемость", "forbidden")
    return repo.student_report(conn, student_id)
