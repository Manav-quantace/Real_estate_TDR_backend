from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_principal
from app.core.deps_params import require_workflow_project_scope
from app.db.session import get_db
from app.schemas.params import ParamsInitResponse, PublishedParamsSnapshot
from app.schemas.primitives import BidRound
from app.services.params_service import ParamsService
from app.models.project import Project
from app.services.audit_service import audit_event, AuditAction
from app.services.subsidized_valuer_service import SubsidizedValuerService

router = APIRouter(prefix="/params")


def _to_snapshot(payload: dict) -> PublishedParamsSnapshot:
    rd = payload.get("round") or {}
    return PublishedParamsSnapshot(
        t=int(payload.get("t", 0)),
        round=BidRound(
            t=int(rd.get("t", 0)),
            state=str(rd.get("state", "draft")),
            bidding_window_start=rd.get("bidding_window_start"),
            bidding_window_end=rd.get("bidding_window_end"),
            is_open=bool(rd.get("is_open", False)),
            is_locked=bool(rd.get("is_locked", False)),
        ),
        inventory=payload.get("inventory") or {},
        government_charges=payload.get("government_charges") or {},
        published_at_iso=None,
    )


def _sanitize_for_public(payload: dict) -> dict:
    """
    Role-based visibility filter:
    This endpoint must not leak any private bid details.
    Snapshots are already meant to be publishable, but we still whitelist keys.
    """
    allowed_top = {"workflow", "projectId", "t", "round", "inventory", "government_charges"}
    return {k: payload.get(k) for k in allowed_top if k in payload}


@router.get("/init", response_model=ParamsInitResponse, dependencies=[Depends(require_workflow_project_scope)])
async def params_init(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    project_id_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(project_id_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be a UUID (Part 2 Project.id).")

    # ensure project exists (workflow-scoped)
    project = db.query(Project).filter(Project.workflow == workflow, Project.id == project_uuid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found for workflow/projectId.")

    service = ParamsService()
    t0_snap, current_snap = service.get_or_create_snapshots(
        db=db,
        workflow=workflow,
        project_uuid=project_uuid,
        published_by_participant_id=principal.participant_id,
    )

    # role-based visibility
    is_privileged = principal.role.value in {"GOV_AUTHORITY", "AUDITOR"}
    visibility = "AUTHORITY/AUDITOR" if is_privileged else "PUBLIC"

    t0_payload = t0_snap.payload_json
    cur_payload = current_snap.payload_json

    if not is_privileged:
        t0_payload = _sanitize_for_public(t0_payload)
        cur_payload = _sanitize_for_public(cur_payload)

    return ParamsInitResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        t0=_to_snapshot(t0_payload),
        current=_to_snapshot(cur_payload),
        visibility=visibility,
    )




"""part 19 require this to be appended here # 5) Hook audit logging into critical actions

You asked to log these actions. The clean pattern is: *call audit_event() at the end of each endpoint/service, with **safe summaries only*.

Below are minimal patches for the key endpoints/services (examples). Add similarly elsewhere.

## 5A) Params init endpoint (Part 5): log “init read”

### app/api/v1/params.py (PATCH)

Add after successful response creation:

python
from app.services.audit_service import audit_event, AuditAction
...
audit_event(
    db,
    request=request,
    actor_participant_id=principal.participant_id,
    actor_role=principal.role.value,
    workflow=workflow,
    project_id=project_uuid,
    t=current_t,
    action=AuditAction.PARAMS_INIT_READ,
    payload_summary={"workflow": workflow, "projectId": str(project_uuid), "t": current_t},
)

"""



""""another patch from part22

# 6) Include valuation in GET /v1/params/init payload

Patch your existing params init handler (Part 5) to append valuation when workflow=subsidized.

### app/api/v1/params.py (PATCH)

Add imports:

python
from app.services.subsidized_valuer_service import SubsidizedValuerService


Inside the handler after you load the project and build payload:

python
valuation = None
if workflow == "subsidized":
    v = SubsidizedValuerService().get_latest(db, workflow="subsidized", project_id=project_uuid)
    if v:
        valuation = {
            "version": v.version,
            "valuation_inr": str(v.valuation_inr) if v.valuation_inr is not None else None,
            "status": v.status,
            "valued_at_iso": v.valued_at.isoformat() if v.valued_at else None,
            "signed_by_participant_id": v.signed_by_participant_id,
        }

payload["independent_valuer_valuation"] = valuation


> This is *display-only*. No calculation."""