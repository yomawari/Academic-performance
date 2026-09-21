from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, status

from ..audit import write_audit
from ..contract.models import Student, StudentCreate, StudentUpdate
from ..db import get_db
from ..deps import get_current_user, require_admin
from ..errors import APIError
from ..repositories import students as repo

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.get("", response_model=list[Student])
def list_students(
    group_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, max_length=100),
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return repo.list_all(
        conn,
        group_id=group_id,
        search=search,
        only_user_id=user["id"] if user["role"] == "student" else None,
    )


@router.post("", response_model=Student, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    student = repo.create(
        conn,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        group_id=payload.group_id,
        record_book_no=payload.record_book_no,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
    )
    write_audit(conn, admin["id"], "create", "student", student["id"])
    return student


@router.get("/{student_id}", response_model=Student)
def get_student(
    student_id: int,
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    student = repo.get(conn, student_id)
    if user["role"] == "student" and student["user_id"] != user["id"]:
        raise APIError(403, "Недостаточно прав для просмотра чужой карточки", "forbidden")
    return student


@router.patch("/{student_id}", response_model=Student)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    fields = payload.model_dump(exclude_unset=True)
    if "email" in fields and fields["email"] is not None:
        fields["email"] = str(fields["email"])
    student = repo.update(conn, student_id, fields)
    write_audit(conn, admin["id"], "update", "student", student_id)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    repo.delete(conn, student_id)
    write_audit(conn, admin["id"], "delete", "student", student_id)
