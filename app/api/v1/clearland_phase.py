# app/api/v1/clearland_phase.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.services.clearland_phase_service import ClearlandPhaseService
from app.models.project import Project
from app.core.deps import strict_workflow_scope
from app.core.clearland_phases import ClearlandPhaseType
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService
from app.models.clearland_phase import ClearlandPhase

router = APIRouter(prefix="/clearland/phase", tags=["clearland"])


@router.get("")
async def get_clearland_phase(
    request: Request,
    projectId: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Read-only endpoint:
    Returns the current clearland phase for a project (projectId passed as query param).
    """
    try:
        project_uuid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    project = (
        db.query(Project)
        .filter(Project.id == project_uuid, Project.workflow == "clearland")
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Clearland project not found.",
        )

    svc = ClearlandPhaseService()
    phase = svc.get_current_phase(db, project_id=project_uuid)

    if not phase:
        return {
            "projectId": projectId,
            "workflow": "clearland",
            "phase": None,
        }

    return {
        "projectId": projectId,
        "workflow": "clearland",
        "phase": {
            "phase": phase.phase,
            "effectiveFrom": phase.effective_from.isoformat(),
            "createdBy": phase.created_by_participant_id,
            "notes": phase.notes_json,
        },
    }


@router.post("/transition", dependencies=[Depends(strict_workflow_scope)])
async def transition_clearland_phase(
    projectId: str,
    targetPhase: ClearlandPhaseType,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Authority only.")

    project_uuid = uuid.UUID(projectId)

    svc = ClearlandPhaseService()
    phase = svc.transition(
        db,
        project_id=project_uuid,
        target_phase=targetPhase,
        actor_participant_id=principal.participant_id,
        notes={"requested_by": principal.display_name},
    )

    # ✅ FIX: supply request_id
    AuditService().write(
        db,
        workflow="clearland",
        project_id=str(project_uuid),
        request_id=str(uuid.uuid4()),  # ← minimal + correct
        t=None,
        actor_participant_id=principal.participant_id,
        action="CLEARLAND_PHASE_TRANSITION",
        details={"phase": targetPhase.value},
    )

    return {
        "projectId": projectId,
        "workflow": "clearland",
        "phase": targetPhase.value,
        "effectiveFrom": phase.effective_from.isoformat(),
    }

@router.get("/current", dependencies=[Depends(strict_workflow_scope)])
def get_current_phase(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if request.state.workflow != "clearland":
        raise HTTPException(status_code=400, detail="Not clearland workflow.")

    project_id = uuid.UUID(request.state.project_id)

    phase = ClearlandPhaseService().get_current(db, project_id=project_id)
    if not phase:
        return {"phase": None}

    return {
        "projectId": str(project_id),
        "phase": phase.phase,
        "effective_from": phase.effective_from.isoformat(),
        "notes": phase.notes_json,
    }


@router.get("/history", dependencies=[Depends(strict_workflow_scope)])
def get_phase_history(
    request: Request,
    projectId: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # Clearland routes are already workflow-scoped
    # ❌ NO workflow check here

    rows = (
        db.query(ClearlandPhase)
        .filter(ClearlandPhase.project_id == projectId)
        .order_by(ClearlandPhase.effective_from.desc())
        .all()
    )

    return [
        {
            "phase": r.phase,
            "effectiveFrom": r.effective_from.isoformat(),
            "createdBy": r.created_by_participant_id,
            "notes": r.notes_json,
        }
        for r in rows
    ]