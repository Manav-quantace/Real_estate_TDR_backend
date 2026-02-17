# app/api/v1/projects.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.policies.projects_policy import (
    can_create_project,
    can_update_project,
    can_publish_project,
)
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectPatchRequest,
    ProjectResponse,
    ProjectListResponse,
)
from app.services.projects_service import ProjectsService
from app.services.audit_service import audit_event, AuditAction

from app.core.types import WorkflowType

router = APIRouter(prefix="/projects")


def _iso(dt):
    return dt.isoformat() if dt else None


def _resp(p) -> dict:
    return {
        "projectId": str(p.id),
        "workflow": p.workflow,
        "title": p.title,
        "status": p.status,
        "isPublished": bool(p.is_published),
        "publishedAtIso": _iso(p.published_at),
        "createdAtIso": _iso(p.created_at),
        "updatedAtIso": _iso(p.updated_at),
        "metadata": p.metadata_json or {},
    }


def _normalize_workflow(raw: str) -> str:
    """
    Accept flexible incoming workflow string and convert to canonical WorkflowType.value.
    Raises HTTPException(400) on invalid workflow.
    """
    if not raw:
        raise HTTPException(status_code=400, detail="Missing workflow parameter.")
    try:
        wf_enum = WorkflowType(raw)
    except Exception:
        try:
            wf_enum = WorkflowType(raw.upper())
        except Exception:
            try:
                wf_enum = WorkflowType(raw.lower())
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid workflow value.")
    return wf_enum.value if hasattr(wf_enum, "value") else str(wf_enum)


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: Request,
    workflow: str = Query(..., min_length=1),
    body: ProjectCreateRequest = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # normalize workflow and use canonical value everywhere
    workflow = _normalize_workflow(workflow)

    if body.workflow.value != workflow:
        # body.workflow is typed as WorkflowType in schema, but still check
        raise HTTPException(
            status_code=400, detail="workflow query must match body.workflow"
        )

    if not can_create_project(principal, workflow):
        raise HTTPException(
            status_code=403, detail="Not permitted to create project for this workflow."
        )

    # ✅ FIXED: metadata is a Pydantic model, not dict
    if body.metadata.kind != workflow:
        raise HTTPException(status_code=400, detail="metadata.kind must match workflow")

    svc = ProjectsService()
    p = svc.create(
        db, workflow=workflow, title=body.title, metadata=body.metadata.model_dump()
    )

    audit_event(
        db,
        request=request,
        actor_participant_id=principal.participant_id,
        actor_role=principal.role.value,
        workflow=workflow,
        project_id=p.id,
        t=None,
        action=AuditAction.PARAMS_PUBLISHED,  # creation/publish lifecycle starts here
        payload_summary={
            "event": "PROJECT_CREATED",
            "projectId": str(p.id),
            "workflow": workflow,
        },
        ref_id=str(p.id),
    )

    return _resp(p)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    workflow: str = Query(..., min_length=1),
    city: str | None = Query(default=None),
    zone: str | None = Query(default=None),
    parcel_size_band: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = _normalize_workflow(workflow)

    # listing allowed for authenticated users (role gates can be tightened later)
    svc = ProjectsService()
    rows = svc.list(
        db,
        workflow=workflow,
        filters={
            "city": city,
            "zone": zone,
            "parcel_size_band": parcel_size_band,
            "status": status,
        },
        limit=limit,
    )
    return {"workflow": workflow, "projects": [_resp(p) for p in rows]}


@router.get("/{projectId}", response_model=ProjectResponse)
async def get_project(
    workflow: str = Query(..., min_length=1),
    projectId: str = "",
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = _normalize_workflow(workflow)

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    p = ProjectsService().get(db, workflow=workflow, project_id=pid)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    return _resp(p)


@router.patch("/{projectId}", response_model=ProjectResponse)
async def patch_project(
    request: Request,
    workflow: str = Query(..., min_length=1),
    projectId: str = "",
    body: ProjectPatchRequest = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = _normalize_workflow(workflow)

    if not can_update_project(principal, workflow):
        raise HTTPException(
            status_code=403, detail="Not permitted to update project for this workflow."
        )
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    # ✅ FIXED here also
    if body.metadata is not None and body.metadata.kind != workflow:
        raise HTTPException(status_code=400, detail="metadata.kind must match workflow")

    svc = ProjectsService()
    try:
        p = svc.patch(
            db,
            workflow=workflow,
            project_id=pid,
            title=body.title,
            status=body.status,
            metadata=body.metadata.model_dump() if body.metadata else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    audit_event(
        db,
        request=request,
        actor_participant_id=principal.participant_id,
        actor_role=principal.role.value,
        workflow=workflow,
        project_id=pid,
        t=None,
        action="PROJECT_UPDATED",
        payload_summary={
            "event": "PROJECT_UPDATED",
            "projectId": str(pid),
            "workflow": workflow,
        },
        ref_id=str(pid),
    )

    return _resp(p)


@router.post("/{projectId}/publish", response_model=ProjectResponse)
async def publish_project(
    request: Request,
    workflow: str = Query(..., min_length=1),
    projectId: str = "",
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = _normalize_workflow(workflow)

    if not can_publish_project(principal, workflow):
        raise HTTPException(
            status_code=403,
            detail="Not permitted to publish project for this workflow.",
        )
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = ProjectsService()
    try:
        p = svc.publish(db, workflow=workflow, project_id=pid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit_event(
        db,
        request=request,
        actor_participant_id=principal.participant_id,
        actor_role=principal.role.value,
        workflow=workflow,
        project_id=pid,
        t=None,
        action="PROJECT_PUBLISHED",
        payload_summary={
            "event": "PROJECT_PUBLISHED",
            "projectId": str(pid),
            "workflow": workflow,
        },
        ref_id=str(pid),
    )

    return _resp(p)
