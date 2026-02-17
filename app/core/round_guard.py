from __future__ import annotations

import uuid
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.round import Round


def require_round_open_for_bid(db: Session, request: Request, workflow: str, project_id_str: str, t: int) -> None:
    try:
        project_id = uuid.UUID(project_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID for round enforcement.")

    rnd = db.execute(
        select(Round).where(Round.workflow == workflow, Round.project_id == project_id, Round.t == t)
    ).scalar_one_or_none()

    if not rnd:
        raise HTTPException(status_code=404, detail="Round not found for workflow/projectId/t.")
    if rnd.is_locked:
        raise HTTPException(status_code=409, detail="Round is locked; bids are immutable.")
    if not rnd.is_open:
        raise HTTPException(status_code=409, detail="Round is closed; bid submissions are not allowed.")