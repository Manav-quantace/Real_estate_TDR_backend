#app/api/v1/clearland_project_memberships.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import strict_workflow_scope
from app.core.auth_deps import get_current_principal
from app.models.clearland_project_memberships import ClearlandProjectMembership

router = APIRouter(prefix="/clearland/memberships", tags=["clearland"])


@router.post("/enroll", dependencies=[Depends(strict_workflow_scope)])
def enroll(
    request: Request,
    participant_id: str,
    role: str,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Authority only.")

    project_id = uuid.UUID(request.state.project_id)

    row = ClearlandProjectMembership(
        project_id=project_id,
        participant_id=participant_id,
        role=role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"status": "enrolled"}


@router.post("/remove", dependencies=[Depends(strict_workflow_scope)])
def remove(
    request: Request,
    participant_id: str,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Authority only.")

    project_id = uuid.UUID(request.state.project_id)

    row = (
        db.query(ClearlandProjectMembership)
        .filter_by(project_id=project_id, participant_id=participant_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Not enrolled.")

    row.status = "removed"
    db.commit()

    return {"status": "removed"}

@router.get("/list", dependencies=[Depends(strict_workflow_scope)])
def list_members(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    project_id = uuid.UUID(request.state.project_id)

    rows = (
        db.query(ClearlandProjectMembership)
        .filter_by(project_id=project_id)
        .all()
    )

    return [
        {
            "participant_id": r.participant_id,
            "role": r.role,
            "status": r.status,
            "enrolled_at": r.enrolled_at.isoformat(),
        }
        for r in rows
    ]