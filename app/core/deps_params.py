# app/core/deps_params.py
from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.types import WorkflowType

async def require_workflow_project_scope(request: Request) -> None:
    """
    Dependecy used on endpoints that require both workflow and projectId scope.
    Accepts workflow and projectId from either query params or path params.

    This function normalizes the workflow to the canonical WorkflowType.value
    (so both "saleable" and "SALEABLE" resolve to the same canonical value).
    """
    wf_raw = request.query_params.get("workflow") or request.path_params.get("workflow")
    pid = (
        request.query_params.get("projectId")
        or request.path_params.get("projectId")
        or request.path_params.get("project_id")
    )

    if not wf_raw or not pid:
        raise HTTPException(
            status_code=400,
            detail="Missing required scope: workflow and projectId are mandatory.",
        )

    # Try to accept common variants: same-case, lowercase, uppercase
    wf_enum = None
    try:
        wf_enum = WorkflowType(wf_raw)
    except Exception:
        try:
            wf_enum = WorkflowType(wf_raw.upper())
        except Exception:
            try:
                wf_enum = WorkflowType(wf_raw.lower())
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid workflow value.")

    # Normalized canonical string (what other code expects)
    normalized_workflow = wf_enum.value if hasattr(wf_enum, "value") else str(wf_enum)

    request.state.workflow = normalized_workflow
    request.state.project_id = pid