from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, status

from ..audit import write_audit
from ..contract.models import Lesson, LessonCreate, LessonUpdate
from ..db import get_db
from ..deps import get_current_user, require_admin
from ..repositories import lessons as repo

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("", response_model=list[Lesson])
def list_lessons(
    group_id: int | None = Query(default=None, ge=1),
    subject_id: int | None = Query(default=None, ge=1),
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return repo.list_all(
        conn,
        group_id=group_id,
        subject_id=subject_id,
        only_user_id=user["id"] if user["role"] == "student" else None,
    )


@router.post("", response_model=Lesson, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: LessonCreate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    values = payload.model_dump()
    values["lesson_date"] = payload.lesson_date.isoformat()
    values["lesson_type"] = str(payload.lesson_type or "practice")
    if values.get("teacher_id") is None:
        values["teacher_id"] = repo.subject_teacher(conn, payload.subject_id)
    lesson = repo.create(conn, values)
    write_audit(conn, admin["id"], "create", "lesson", lesson["id"])
    return lesson


@router.get("/{lesson_id}", response_model=Lesson)
def get_lesson(
    lesson_id: int,
    _user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return repo.get(conn, lesson_id)


@router.patch("/{lesson_id}", response_model=Lesson)
def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    values = payload.model_dump(exclude_unset=True)
    if "lesson_date" in values and values["lesson_date"] is not None:
        values["lesson_date"] = values["lesson_date"].isoformat()
    if "lesson_type" in values and values["lesson_type"] is not None:
        values["lesson_type"] = str(values["lesson_type"])
    lesson = repo.update(conn, lesson_id, values)
    write_audit(conn, admin["id"], "update", "lesson", lesson_id)
    return lesson


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    repo.delete(conn, lesson_id)
    write_audit(conn, admin["id"], "delete", "lesson", lesson_id)
