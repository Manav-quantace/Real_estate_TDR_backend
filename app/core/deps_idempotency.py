from __future__ import annotations

import uuid
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.services.idempotency_service import IdempotencyService


async def require_idempotency_key(request: Request) -> str:
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key header.")
    if len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key too long.")
    return key


async def idempotency_guard(
    request: Request,
    idem_key: str = Depends(require_idempotency_key),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Use inside POST bid endpoints.

    Requires request.state.workflow and request.state.project_id already set by your scope guard.
    Stores in request.state:
      - idem_key
      - request_hash
      - replay_response (optional)
      - replay_status (optional)
    """
    workflow = getattr(request.state, "workflow", None)
    project_id = getattr(request.state, "project_id", None)
    if not workflow or not project_id:
        raise HTTPException(status_code=400, detail="workflow and projectId scope required.")

    try:
        pid = uuid.UUID(str(project_id))
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    endpoint_key = f"{request.method}:{request.url.path}"

    # Read JSON body once and cache it
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    svc = IdempotencyService()
    try:
        replay_json, replay_status, req_hash = svc.reserve_or_replay(
            db,
            workflow=workflow,
            project_id=pid,
            participant_id=principal.participant_id,
            endpoint_key=endpoint_key,
            idem_key=idem_key,
            request_payload=payload if isinstance(payload, dict) else {"_": payload},
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    request.state.idempotency_endpoint_key = endpoint_key
    request.state.idempotency_key = idem_key
    request.state.idempotency_request_hash = req_hash
    request.state.idempotency_replay_json = replay_json
    request.state.idempotency_replay_status = replay_status

    return idem_key