from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status

from ..audit import write_audit
from ..contract.models import Subject, SubjectCreate, SubjectUpdate
from ..db import get_db
from ..deps import get_current_user, require_admin
from ..repositories import subjects as repo

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


@router.get("", response_model=list[Subject])
def list_subjects(
    _: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return repo.list_all(conn)


@router.post("", response_model=Subject, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    subject = repo.create(
        conn,
        code=payload.code,
        title=payload.title,
        description=payload.description or "",
        hours=payload.hours,
        teacher_id=payload.teacher_id,
    )
    write_audit(conn, admin["id"], "create", "subject", subject["id"])
    return subject


@router.patch("/{subject_id}", response_model=Subject)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    subject = repo.update(conn, subject_id, payload.model_dump(exclude_unset=True))
    write_audit(conn, admin["id"], "update", "subject", subject_id)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    repo.delete(conn, subject_id)
    write_audit(conn, admin["id"], "delete", "subject", subject_id)
