from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status

from ..audit import write_audit
from ..contract.models import Group, GroupCreate, GroupUpdate
from ..db import get_db
from ..deps import get_current_user, require_admin
from ..repositories import groups as repo

router = APIRouter(prefix="/api/groups", tags=["Groups"])


@router.get("", response_model=list[Group])
def list_groups(
    _: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return repo.list_all(conn)


@router.post("", response_model=Group, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    group = repo.create(
        conn,
        name=payload.name,
        course=payload.course,
        curator_id=payload.curator_id,
    )
    write_audit(conn, admin["id"], "create", "group", group["id"])
    return group


@router.patch("/{group_id}", response_model=Group)
def update_group(
    group_id: int,
    payload: GroupUpdate,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    group = repo.update(conn, group_id, payload.model_dump(exclude_unset=True))
    write_audit(conn, admin["id"], "update", "group", group_id)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    admin: dict = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    repo.delete(conn, group_id)
    write_audit(conn, admin["id"], "delete", "group", group_id)
