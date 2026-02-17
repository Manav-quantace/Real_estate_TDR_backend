from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_principal
from app.core.deps_params import require_workflow_project_scope
from app.db.session import get_db
from app.schemas.charges import ChargeResponse
from app.services.charges_service import ChargesService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/charges")


def _require_t(t: int | None) -> int:
    if t is None or t < 0:
        raise HTTPException(
            status_code=400, detail="Missing or invalid t (round index)."
        )
    return t


def _must_be_authority(principal) -> None:
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(
            status_code=403, detail="Only GOV_AUTHORITY may trigger recalculation."
        )


@router.get(
    "/gc",
    response_model=ChargeResponse,
    dependencies=[Depends(require_workflow_project_scope)],
)
async def get_gc(
    request: Request,
    t: int = Query(..., ge=0),
    recalc: bool = Query(False),
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(
            status_code=400, detail="projectId must be a UUID (Project.id)."
        )

    t = _require_t(t)

    svc = ChargesService()
    rnd = svc.get_round(db, workflow, project_uuid, t)
    if not rnd:
        raise HTTPException(
            status_code=404, detail="Round not found for project/workflow/t."
        )

    charge = svc.get_or_create_charge(
        db,
        workflow=workflow,
        project_id=project_uuid,
        round_id=rnd.id,
        charge_type="GC",
    )

    calculated = charge.value_inr is not None
    if recalc:
        _must_be_authority(principal)
        try:
            charge = svc.recalc_charge(
                db, charge=charge, actor_participant_id=principal.participant_id
            )
            calculated = True
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        AuditService().write(
            db,
            workflow=workflow,
            project_id=str(project_uuid),
            t=t,
            actor_participant_id=principal.participant_id,
            action="GC_RECALCULATED",
            request_id=getattr(request.state, "request_id", None),
            details={"charge_id": str(charge.id), "round_id": str(rnd.id)},
        )

    return ChargeResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        t=t,
        charge_type="GC",
        weights=charge.weights_json or {},
        inputs=charge.inputs_json or {},
        value_inr=charge.value_inr,
        calculated=calculated,
        audit_ref=f"/v1/ledger/audit?workflow={workflow}&projectId={project_uuid}&t={t}",
    )


@router.get(
    "/gcu",
    response_model=ChargeResponse,
    dependencies=[Depends(require_workflow_project_scope)],
)
async def get_gcu(
    request: Request,
    t: int = Query(..., ge=0),
    recalc: bool = Query(False),
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(
            status_code=400, detail="projectId must be a UUID (Project.id)."
        )

    t = _require_t(t)

    svc = ChargesService()
    rnd = svc.get_round(db, workflow, project_uuid, t)
    if not rnd:
        raise HTTPException(
            status_code=404, detail="Round not found for project/workflow/t."
        )

    charge = svc.get_or_create_charge(
        db,
        workflow=workflow,
        project_id=project_uuid,
        round_id=rnd.id,
        charge_type="GCU",
    )

    calculated = charge.value_inr is not None
    if recalc:
        _must_be_authority(principal)
        try:
            charge = svc.recalc_charge(
                db, charge=charge, actor_participant_id=principal.participant_id
            )
            calculated = True
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        AuditService().write(
            db,
            workflow=workflow,
            project_id=str(project_uuid),
            t=t,
            actor_participant_id=principal.participant_id,
            action="GCU_RECALCULATED",
            request_id=getattr(request.state, "request_id", None),
            details={"charge_id": str(charge.id), "round_id": str(rnd.id)},
        )

    return ChargeResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        t=t,
        charge_type="GCU",
        weights=charge.weights_json or {},
        inputs=charge.inputs_json or {},
        value_inr=charge.value_inr,
        calculated=calculated,
        audit_ref=f"/v1/ledger/audit?workflow={workflow}&projectId={project_uuid}&t={t}",
    )
