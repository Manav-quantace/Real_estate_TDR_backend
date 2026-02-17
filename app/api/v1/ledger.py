# app/api/v1/ledger.py

from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.core.deps_params import require_workflow_project_scope
from app.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ledger", tags=["ledger"])


def _authority_or_auditor(principal):
    if principal.role.value not in {"GOV_AUTHORITY", "AUDITOR"}:
        raise HTTPException(
            status_code=403,
            detail="Only authority or auditor may access ledger.",
        )


@router.get(
    "",
    dependencies=[Depends(require_workflow_project_scope)],
)
async def list_ledger_entries(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    """
    Read-only ledger view.
    Economic source of truth.
    """
    logger.info("[ledger] request principal=%s workflow-state=%s", getattr(principal, "participant_id", "<none>"), getattr(request.state, "workflow", "<none>"))
    _authority_or_auditor(principal)

    workflow = request.state.workflow
    project_id_raw = request.state.project_id

    logger.debug("[ledger] workflow=%s project_id=%s", workflow, project_id_raw)

    try:
        project_uuid = uuid.UUID(project_id_raw)
    except Exception as exc:
        logger.warning("[ledger] invalid projectId UUID: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid projectId UUID.")

    svc = LedgerService()
    entries = svc.list_entries(
        db,
        workflow=workflow,
        project_id=project_uuid,
    )

    logger.info("[ledger] returning %d entries for project %s", len(entries), project_id_raw)

    return [
        {
            "seq": e.seq,
            "entry_type": e.entry_type,
            "contract_id": str(e.contract_id),
            "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash,
            "created_at": e.created_at.isoformat(),
            "payload": e.payload_json,
        }
        for e in entries
    ]


@router.get(
    "/verify",
    dependencies=[Depends(require_workflow_project_scope)],
)
async def verify_ledger_chain(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    """
    Verifies hash-chain integrity.
    Auditor-grade endpoint.
    """
    logger.info("[ledger/verify] principal=%s workflow-state=%s", getattr(principal, "participant_id", "<none>"), getattr(request.state, "workflow", "<none>"))
    _authority_or_auditor(principal)

    workflow = request.state.workflow
    project_id_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(project_id_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId UUID.")

    ok = LedgerService().verify_chain(
        db,
        workflow=workflow,
        project_id=project_uuid,
    )

    logger.info("[ledger/verify] project=%s valid=%s", project_id_raw, ok)

    return {
        "workflow": workflow,
        "projectId": project_id_raw,
        "valid": ok,
    }
