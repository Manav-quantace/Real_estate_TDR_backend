from fastapi import APIRouter, Depends
from app.core.deps import strict_workflow_scope
from app.core.auth_deps import get_current_principal

router = APIRouter(prefix="/ledger/audit")


@router.get("", dependencies=[Depends(strict_workflow_scope)])
async def get_audit_log(_principal=Depends(get_current_principal)):
    return {"status": "stub", "message": "Audit log (stub). Auth enforced."}