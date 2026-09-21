from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status

from ..audit import write_audit
from ..contract.models import Teacher, TeacherCreate, TeacherUpdate
from ..db import get_db
from ..deps import get_current_user, require_admin
from ..repositories import teachers as repo

router = APIRouter(prefix="/api/teachers", tags=["Teachers"])


@router.get("", response_model=list[Teacher])
def list_teachers(
    _: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return repo.list_all(conn)


@router.post("", response_model=Teacher, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    teacher = repo.create(
        conn,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        department=payload.department,
        position=payload.position,
    )
    write_audit(conn, admin["id"], "create", "teacher", teacher["id"])
    return teacher


@router.patch("/{teacher_id}", response_model=Teacher)
def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    teacher = repo.update(conn, teacher_id, payload.model_dump(exclude_unset=True))
    write_audit(conn, admin["id"], "update", "teacher", teacher_id)
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: int,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    repo.delete(conn, teacher_id)
    write_audit(conn, admin["id"], "delete", "teacher", teacher_id)
