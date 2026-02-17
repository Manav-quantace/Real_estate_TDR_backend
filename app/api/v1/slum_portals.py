#app/api/v1/slum_portals.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.project import Project
from app.models.slum_portal_membership import SlumPortalMembership
from app.core.slum_types import SlumPortalType
from app.schemas.slum_portals import SlumPortalsResponse

router = APIRouter(prefix="/slum")


@router.get("/portals", response_model=SlumPortalsResponse)
async def get_slum_portals(
    workflow: str = Query(..., min_length=1),
    projectId: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if workflow != "slum":
        raise HTTPException(status_code=400, detail="workflow must be slum.")

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    proj = db.execute(select(Project).where(Project.workflow == "slum", Project.id == pid)).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Slum project not found.")

    md = proj.metadata_json or {}

    enabled_map = {
        SlumPortalType.SLUM_DWELLER.value: bool(md.get("portal_slum_dweller_enabled", True)),
        SlumPortalType.SLUM_LAND_DEVELOPER.value: bool(md.get("portal_slum_land_developer_enabled", True)),
        SlumPortalType.AFFORDABLE_HOUSING_DEV.value: bool(md.get("portal_affordable_housing_dev_enabled", True)),
    }

    memberships = db.execute(
        select(SlumPortalMembership.portal_type).where(
            SlumPortalMembership.workflow == "slum",
            SlumPortalMembership.project_id == pid,
            SlumPortalMembership.participant_id == principal.participant_id,
        )
    ).scalars().all()
    member_set = set(memberships or [])

    portals = []
    for ptype, enabled in enabled_map.items():
        portals.append({
            "portalType": ptype,
            "enabled": enabled,
            "member": ptype in member_set,
        })

    return {
        "workflow": "slum",
        "projectId": projectId,
        "portals": portals,
    }

