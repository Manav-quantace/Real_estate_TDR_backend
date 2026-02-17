#app/api/v1/slum_enroll.py
from __future__ import annotations

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_portal_membership import SlumPortalMembership
from app.models.project import Project
from app.schemas.slum_enroll import SlumPortalEnrollRequest
from app.core.slum_types import SlumPortalType

router = APIRouter(prefix="/slum")



# OPTIONAL: If you have a Participant model (likely), import it to include display_name.
# If you don't have this model, the code will still return participant_id and portal_type.
try:
    from app.models.participant import Participant  # adjust path/name if different
    HAVE_PARTICIPANT_MODEL = True
except Exception:
    HAVE_PARTICIPANT_MODEL = False

router = APIRouter(prefix="/slum")

# --- existing enroll endpoint assumed here (unchanged) ---

@router.post("/enroll")
async def enroll_participant(
    request: Request,
    body: SlumPortalEnrollRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(
            status_code=403, detail="Only authority can enroll slum portal members."
        )

    if body.workflow.value != "slum":
        raise HTTPException(status_code=400, detail="workflow must be slum.")
    try:
        pid = uuid.UUID(body.projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    proj = db.execute(
        select(Project).where(Project.workflow == "slum", Project.id == pid)
    ).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Slum project not found.")

    try:
        portal = SlumPortalType(body.portalType)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid portalType.")

    # Insert membership idempotently
    existing = db.execute(
        select(SlumPortalMembership).where(
            SlumPortalMembership.workflow == "slum",
            SlumPortalMembership.project_id == pid,
            SlumPortalMembership.participant_id == body.participantId,
            SlumPortalMembership.portal_type == portal.value,
        )
    ).scalar_one_or_none()
    if existing:
        return {"status": "already_enrolled"}

    row = SlumPortalMembership(
        workflow="slum",
        project_id=pid,
        participant_id=body.participantId,
        portal_type=portal.value,
    )
    db.add(row)
    db.commit()
    return {"status": "enrolled", "portalType": portal.value}


@router.get("/memberships")
def list_memberships(
    projectId: str = Query(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> List[dict]:
    """
    Returns all SlumPortalMembership rows for a project.

    Response: [{ "participant_id": "...", "portal_type": "...", "display_name": "..." }, ...]
    """
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    # Authorize: require authority or project admin — adapt to your rules.
    # Here we allow any authenticated principal to view project memberships.
    # (Change to stricter check if you need.)
    # Confirm project exists (optional)
    proj = db.execute(
        select(Project).where(Project.workflow == "slum", Project.id == pid)
    ).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Slum project not found.")

    rows = (
        db.query(SlumPortalMembership)
        .filter(
            SlumPortalMembership.workflow == "slum",
            SlumPortalMembership.project_id == pid,
        )
        .all()
    )

    result = []
    for r in rows:
        item = {
            "participant_id": str(r.participant_id),
            "portal_type": r.portal_type,
        }
        # try to add display_name if Participant model exists
        if HAVE_PARTICIPANT_MODEL:
            p = db.execute(
                select(Participant).where(Participant.id == r.participant_id)
            ).scalar_one_or_none()
            if p:
                item["display_name"] = getattr(p, "display_name", None) or getattr(p, "name", None)
        result.append(item)

    return result


@router.post("/enroll/remove")
def remove_membership(
    body: SlumPortalEnrollRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Remove an enrollment/membership.
    Body: same schema as enroll: { workflow, projectId, participantId, portalType }
    """
    # Only gov authority may remove (same guard as enroll) — adapt as needed
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Only authority can remove slum portal members.")

    if body.workflow.value != "slum":
        raise HTTPException(status_code=400, detail="workflow must be slum.")
    try:
        pid = uuid.UUID(body.projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    try:
        portal = SlumPortalType(body.portalType)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid portalType.")

    # find membership
    membership = db.execute(
        select(SlumPortalMembership).where(
            SlumPortalMembership.workflow == "slum",
            SlumPortalMembership.project_id == pid,
            SlumPortalMembership.participant_id == body.participantId,
            SlumPortalMembership.portal_type == portal.value,
        )
    ).scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found.")

    # delete
    db.execute(
        delete(SlumPortalMembership).where(SlumPortalMembership.id == membership.id)
    )
    db.commit()

    return {"status": "removed", "portalType": portal.value, "participantId": body.participantId}