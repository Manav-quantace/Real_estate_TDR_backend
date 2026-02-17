# app/api/v1/participants.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.participants import ParticipantCreate
from app.models.participant import Participant
from app.core.security import hash_password
from app.core.auth_deps import get_current_principal
from app.models.enums import ParticipantRole

router = APIRouter(prefix="/admin/participants", tags=["admin"])


# ✅ LIST PARTICIPANTS (needed for slum portal enrollment UI)
@router.get("")
def list_participants(
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if principal.role != ParticipantRole.GOV_AUTHORITY:
        raise HTTPException(status_code=403, detail="Authority only")

    rows = db.query(Participant).all()

    return [
        {
            "id": str(p.id),
            "display_name": p.display_name,
            "role": p.role,
            "workflow": p.workflow,
        }
        for p in rows
    ]


# ✅ CREATE PARTICIPANT (already existed, kept intact)
@router.post("")
def create_participant(
    req: ParticipantCreate,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if principal.role != ParticipantRole.GOV_AUTHORITY:
        raise HTTPException(status_code=403, detail="Authority only")

    exists = (
        db.query(Participant)
        .filter(
            Participant.workflow == req.workflow,
            Participant.username == req.username,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Participant already exists")

    p = Participant(
        workflow=req.workflow,
        username=req.username,
        password_hash=hash_password(req.password),
        role=req.role.value,
        display_name=req.display_name,
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    return {"id": str(p.id)}
