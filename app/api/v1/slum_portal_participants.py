#app/api/v1/slum_portal_participants.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, cast
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_portal_membership import SlumPortalMembership
from app.models.participant import Participant

router = APIRouter(prefix="/slum/portal")


@router.get("/participants")
def get_slum_portal_participants(
    projectId: str = Query(...),
    portalType: str = Query(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # 🔐 Authority-only
    if principal.role != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Authority access required")

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    rows = (
        db.execute(
            select(
                SlumPortalMembership.participant_id,
                Participant.display_name,
                Participant.role,
            )
            .join(
                Participant,
                Participant.id == cast(
                    SlumPortalMembership.participant_id,
                    PG_UUID
                ),
            )
            .where(
                SlumPortalMembership.workflow == "slum",
                SlumPortalMembership.project_id == pid,
                SlumPortalMembership.portal_type == portalType,
            )
        )
        .all()
    )

    return [
        {
            "participant_id": r.participant_id,
            "display_name": r.display_name,
            "role": r.role,
        }
        for r in rows
    ]
