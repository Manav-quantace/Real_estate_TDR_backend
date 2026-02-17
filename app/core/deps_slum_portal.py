#app/core/deps_slum_portal.py
from __future__ import annotations

import uuid
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.slum_types import SlumPortalType
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_portal_membership import SlumPortalMembership


ROLE_FOR_PORTAL = {
    SlumPortalType.SLUM_DWELLER: {"SLUM_DWELLER"},
    SlumPortalType.SLUM_LAND_DEVELOPER: {"DEVELOPER"},
    SlumPortalType.AFFORDABLE_HOUSING_DEV: {"AFFORDABLE_HOUSING_DEV"},
}


def require_slum_portal_access(portal: SlumPortalType):
    async def _dep(
        request: Request,
        db: Session = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        workflow = getattr(request.state, "workflow", None) or request.query_params.get("workflow")
        project_id = getattr(request.state, "project_id", None) or request.query_params.get("projectId")

        if workflow != "slum":
            raise HTTPException(status_code=400, detail="workflow must be slum for slum portal access.")
        if not project_id:
            raise HTTPException(status_code=400, detail="projectId is required.")

        try:
            pid = uuid.UUID(str(project_id))
        except Exception:
            raise HTTPException(status_code=400, detail="projectId must be UUID.")

        if principal.role.value not in ROLE_FOR_PORTAL[portal]:
            raise HTTPException(status_code=403, detail="Role not permitted for this slum portal.")

        row = db.execute(
            select(SlumPortalMembership).where(
                SlumPortalMembership.workflow == "slum",
                SlumPortalMembership.project_id == pid,
                SlumPortalMembership.participant_id == principal.participant_id,
                SlumPortalMembership.portal_type == portal.value,
            )
        ).scalar_one_or_none()

        if not row:
            raise HTTPException(status_code=403, detail="Participant not enrolled in this slum project portal.")
        return principal

    return _dep