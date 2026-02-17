# /app/core/deps.py
from typing import Optional, Tuple
from fastapi import Request, HTTPException
from app.core.types import WorkflowType
import uuid

WORKFLOW_REQUIRED_PREFIXES = (
    "/api/v1/bids",
    "/api/v1/matching",
    "/api/v1/settlement",
    "/api/v1/ledger/audit",
    "/api/v1/contracts",
)


def _extract_workflow_and_project(
    request: Request,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolution order:
    1. Headers
    2. Path params
    3. Query params
    """
    wf = request.headers.get("x-workflow")
    pid = request.headers.get("x-project-id")

    if not wf:
        wf = request.path_params.get("workflow")
    if not pid:
        pid = request.path_params.get("project_id") or request.path_params.get(
            "projectId"
        )

    if not wf:
        wf = request.query_params.get("workflow")
    if not pid:
        pid = request.query_params.get("projectId") or request.query_params.get(
            "project_id"
        )

    return wf, pid


async def strict_workflow_scope(request: Request) -> None:
    """
    Enforces project scoping always.
    Enforces workflow ONLY for core economic routes.

    Safe for Clearland read APIs.
    """

    path = request.url.path
    wf_raw, project_id = _extract_workflow_and_project(request)

    # 🔒 projectId is ALWAYS required
    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required scope: projectId",
        )

    try:
        project_uuid = uuid.UUID(str(project_id))
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    # 🧠 Detect if workflow is REQUIRED for this route
    workflow_required = path.startswith(WORKFLOW_REQUIRED_PREFIXES)

    # If workflow is required, enforce it strictly
    if workflow_required:
        if not wf_raw:
            raise HTTPException(
                status_code=400,
                detail="Missing required scope: workflow",
            )

        try:
            wf_enum = WorkflowType(wf_raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid workflow value.")

        request.state.workflow = wf_enum.value

    else:
        # 🟢 Clearland / other scoped routers
        # Auto-bind workflow if absent
        if wf_raw:
            try:
                wf_enum = WorkflowType(wf_raw)
                request.state.workflow = wf_enum.value
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid workflow value.")
        else:
            # infer from router (clearland router = clearland)
            request.state.workflow = "clearland"

    request.state.project_id = str(project_uuid)
