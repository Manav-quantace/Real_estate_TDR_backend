from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.policies.export_policy import export_scope

from app.core.streaming import csv_stream
from app.services.export_audit_service import ExportAuditService
from app.services.export_contracts_service import ExportContractsService
from app.services.export_settlement_service import ExportSettlementService

router = APIRouter(prefix="/export")


def _uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")


@router.get("/audit.csv")
async def export_audit_csv(
    workflow: str = Query(..., min_length=1),
    projectId: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    pid = _uuid(projectId)
    scope = export_scope(principal)

    svc = ExportAuditService()
    rows = svc.iter_rows(db, scope=scope, workflow=workflow, project_id=pid)
    fieldnames = svc.fieldnames()

    filename = f"audit_{workflow}_{projectId}.csv"
    return StreamingResponse(
        csv_stream(rows, fieldnames),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/contracts.json")
async def export_contracts_json(
    workflow: str = Query(..., min_length=1),
    projectId: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    pid = _uuid(projectId)
    scope = export_scope(principal)

    svc = ExportContractsService()
    contracts = svc.iter_contract_dicts(db, scope=scope, workflow=workflow, project_id=pid)
    filename = f"contracts_{workflow}_{projectId}.json"

    return StreamingResponse(
        svc.json_stream(contracts),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/settlement.csv")
async def export_settlement_csv(
    workflow: str = Query(..., min_length=1),
    projectId: str = Query(..., min_length=1),
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    pid = _uuid(projectId)
    scope = export_scope(principal)

    svc = ExportSettlementService()
    rows = svc.iter_rows(db, scope=scope, workflow=workflow, project_id=pid, t=t)
    fieldnames = svc.fieldnames()
    filename = f"settlement_{workflow}_{projectId}_t{t}.csv"

    return StreamingResponse(
        csv_stream(rows, fieldnames),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

