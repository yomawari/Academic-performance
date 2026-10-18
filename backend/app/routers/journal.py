from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..audit import write_audit
from ..contract.models import Journal, JournalEntry, JournalUpdate
from ..db import get_db
from ..deps import require_staff
from ..errors import APIError
from ..repositories import journal as repo
from ..repositories import lessons as lessons_repo

router = APIRouter(prefix="/api/lessons", tags=["Journal"])


def _teacher_id(conn: sqlite3.Connection, user_id: int) -> int | None:
    row = conn.execute("SELECT id FROM teachers WHERE user_id = ?", (user_id,)).fetchone()
    return int(row["id"]) if row is not None else None


def _check_access(conn: sqlite3.Connection, lesson: dict, user: dict) -> None:
    if user["role"] == "admin":
        return
    teacher_id = _teacher_id(conn, user["id"])
    if teacher_id is None or lesson["teacher_id"] != teacher_id:
        raise APIError(403, "Можно редактировать журнал только своих занятий", "forbidden")


@router.get("/{lesson_id}/journal", response_model=Journal)
def get_journal(
    lesson_id: int,
    user: dict = Depends(require_staff),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    lesson = lessons_repo.get(conn, lesson_id)
    _check_access(conn, lesson, user)
    return repo.get_journal(conn, lesson_id)


@router.put("/{lesson_id}/journal/{student_id}", response_model=JournalEntry)
def save_journal_entry(
    lesson_id: int,
    student_id: int,
    payload: JournalUpdate,
    user: dict = Depends(require_staff),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    lesson = lessons_repo.get(conn, lesson_id)
    _check_access(conn, lesson, user)
    entry = repo.save_entry(
        conn,
        lesson_id=lesson_id,
        student_id=student_id,
        values=payload.model_dump(exclude_unset=True),
        user_id=user["id"],
    )
    write_audit(
        conn,
        user["id"],
        "update",
        "journal",
        lesson_id,
        {"student_id": student_id},
    )
    return entry
