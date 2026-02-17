# app/api/v1/contracts.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.schemas.contracts import TokenizedContractResponse, ContractListResponse
from app.services.contract_service import ContractService
from app.models.tokenized_contract import TokenizedContractRecord

router = APIRouter(prefix="/contracts")


def _iso(dt):
    return dt.isoformat() if dt else None


def _to_resp(c: TokenizedContractRecord) -> dict:
    return {
        "contractId": str(c.id),
        "workflow": c.workflow,
        "projectId": str(c.project_id),
        "version": c.version,
        "priorContractId": str(c.prior_contract_id) if c.prior_contract_id else None,
        "settlementResultId": str(c.settlement_result_id),
        "createdAtIso": _iso(c.created_at),
        "contractHash": c.contract_hash,
        "ownershipDetails": c.ownership_details_json or {},
        "transactionData": c.transaction_data_json or {},
        "legalObligations": c.legal_obligations_json or {},
    }

@router.get("/byProject", response_model=ContractListResponse, dependencies=[Depends(require_workflow_project_scope)])
async def list_contracts_by_project(
    request: Request,
    db: Session = Depends(get_db),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id
    try:
        pid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = ContractService()

    # If none exists but settlement is settled, create deterministically (idempotent)
    try:
        _ = svc.create_or_get_latest_for_project(db, workflow=workflow, project_id=pid)
    except ValueError:
        # If settlement not ready, we still return an empty list (no invention)
        pass

    rows = svc.list_by_project(db, workflow=workflow, project_id=pid)
    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "contracts": [_to_resp(c) for c in rows],
    }


@router.get("/{contractId}", response_model=TokenizedContractResponse)
async def get_contract(
    contractId: str,
    db: Session = Depends(get_db),
):
    try:
        cid = uuid.UUID(contractId)
    except Exception:
        raise HTTPException(status_code=400, detail="contractId must be UUID.")

    row = ContractService().get_contract(db, cid)
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found.")
    return _to_resp(row)


