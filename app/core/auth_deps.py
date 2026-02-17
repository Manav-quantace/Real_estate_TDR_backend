#app/core/auth_deps.py
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.models.enums import ParticipantRole
from app.policies.rbac import Principal

bearer = HTTPBearer(auto_error=True)


def get_current_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> Principal:
    """
    Canonical authentication dependency.

    Guarantees:
    - JWT is valid
    - workflow, role, participant_id are present
    - role is a valid ParticipantRole
    - workflow matches request scope if enforced upstream
      (EXCEPT for GOV_AUTHORITY which is global)
    """

    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    workflow = payload.get("workflow")
    role = payload.get("role")
    participant_id = payload.get("participant_id")
    display_name = payload.get("display_name") or "Unknown"

    if not role or not participant_id:
        raise HTTPException(status_code=401, detail="Token missing required claims.")

    try:
        role_enum = ParticipantRole(role)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid role in token.")

    # Enforce workflow scoping if middleware populated it
    scoped_workflow = getattr(request.state, "workflow", None)

    # 🚨 AUTHORITY BYPASSES WORKFLOW SCOPE
    if role_enum != ParticipantRole.GOV_AUTHORITY:
        if not workflow:
            raise HTTPException(status_code=401, detail="Token missing workflow claim.")

        if scoped_workflow and scoped_workflow != workflow:
            raise HTTPException(status_code=403, detail="Token workflow scope mismatch.")

    principal = Principal(
        participant_id=str(participant_id),
        workflow=str(workflow) if workflow else None,
        role=role_enum,
        display_name=str(display_name),
    )

    # Make principal available to downstream middleware / handlers
    request.state.principal = principal

    return principal
