#app/api/v1/slum_consents.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_consent import SlumConsent

router = APIRouter(prefix="/slum/consents")

PORTAL_ROLES = {
    "SLUM_DWELLER",
    "AFFORDABLE_HOUSING_DEV",
    "DEVELOPER",
}


class ConsentIn(BaseModel):
    text: str


def resolve_target_participant(
    principal: Principal, participantId: str | None
) -> str:
    if participantId:
        if principal.role in PORTAL_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Not allowed to access other participant data",
            )
        try:
            uuid.UUID(participantId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid participantId")
        return participantId

    return principal.participant_id


@router.post("/submit")
def submit_consent(
    projectId: str = Query(...),
    portalType: str = Query(...),
    payload: ConsentIn = Body(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    existing = (
        db.query(SlumConsent)
        .filter(
            SlumConsent.workflow == "slum",
            SlumConsent.project_id == pid,
            SlumConsent.portal_type == portalType,
            SlumConsent.participant_id == principal.participant_id,
        )
        .first()
    )

    if existing:
        return {"exists": True, "agreed": existing.agreed}

    consent = SlumConsent(
        workflow="slum",
        project_id=pid,
        participant_id=principal.participant_id,
        portal_type=portalType,
        consent_text=payload.text,
        agreed=True,
    )

    db.add(consent)
    db.commit()

    return {"exists": True, "agreed": True}


@router.get("")
def get_consent(
    projectId: str = Query(...),
    portalType: str = Query(...),
    participantId: str | None = Query(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    target_participant = resolve_target_participant(principal, participantId)

    consent = (
        db.query(SlumConsent)
        .filter(
            SlumConsent.workflow == "slum",
            SlumConsent.project_id == pid,
            SlumConsent.portal_type == portalType,
            SlumConsent.participant_id == target_participant,
        )
        .first()
    )

    if not consent:
        return {"exists": False}

    return {
        "exists": True,
        "agreed": consent.agreed,
        "text": consent.consent_text,
        "created_at": consent.created_at,
    }
