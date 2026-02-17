from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from app.db.session import get_db
from app.models.project import Project
from app.models.parameter_snapshot import ParameterSnapshot
from app.models.round import Round
from app.schemas.saleable import (
    SaleableCreate,
    SaleableUpdate,
    SaleableProjectOut,
)

router = APIRouter(prefix="/saleable", tags=["saleable"])

WORKFLOW = "saleable"


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

@router.get("/dashboard")
def saleable_dashboard(db: Session = Depends(get_db)):
    projects = (
        db.query(Project)
        .filter(Project.workflow == WORKFLOW)
        .order_by(Project.created_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "project_id": str(p.id),
                "title": p.title,
                "status": p.status,
                "is_published": p.is_published,
            }
            for p in projects
        ]
    }


# ─────────────────────────────────────────────────────────────
# CREATE PROJECT
# ─────────────────────────────────────────────────────────────

@router.post("/projects")
def create_saleable_project(
    body: SaleableCreate,
    db: Session = Depends(get_db),
):
    project = Project(
        id=uuid.uuid4(),
        workflow=WORKFLOW,
        title=body.title,
        status="draft",
        is_published=False,
    )

    db.add(project)
    db.flush()  # ensure project.id available

    # initial round t=0 (DRAFT, CLOSED by default)
    round0 = Round(
        workflow=WORKFLOW,
        project_id=project.id,
        t=0,
        is_open=False,
        is_locked=False,
        state="draft",
    )
    db.add(round0)

    # initial parameter snapshot t=0
    snapshot = ParameterSnapshot(
        workflow=WORKFLOW,
        project_id=project.id,
        t=0,
        payload_json=body.params,
    )
    db.add(snapshot)

    if body.action == "publish":
        project.is_published = True
        project.status = "published"
        project.published_at = func.now()

    db.commit()

    return {"project_id": str(project.id)}


# ─────────────────────────────────────────────────────────────
# GET PROJECT (SAFE)
# ─────────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}",
    response_model=SaleableProjectOut,
)
def get_saleable_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workflow == WORKFLOW,
        )
        .one_or_none()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    snapshot = (
        db.query(ParameterSnapshot)
        .filter(
            ParameterSnapshot.workflow == WORKFLOW,
            ParameterSnapshot.project_id == project.id,
            ParameterSnapshot.t == 0,
        )
        .one_or_none()
    )

    # ✅ FIX: tolerate legacy projects
    params = snapshot.payload_json if snapshot else {}

    return {
        "project_id": str(project.id),
        "title": project.title,
        "status": project.status,
        "is_published": project.is_published,
        "published_at": project.published_at,
        "params": params,
    }


# ─────────────────────────────────────────────────────────────
# UPDATE PROJECT (PRE-PUBLISH ONLY)
# ─────────────────────────────────────────────────────────────

@router.put("/projects/{project_id}")
def update_saleable_project(
    project_id: uuid.UUID,
    body: SaleableUpdate,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workflow == WORKFLOW,
        )
        .one_or_none()   # ✅ FIX
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.is_published:
        raise HTTPException(
            status_code=403,
            detail="Metadata locked after publish",
        )

    snapshot = (
        db.query(ParameterSnapshot)
        .filter(
            ParameterSnapshot.workflow == WORKFLOW,
            ParameterSnapshot.project_id == project.id,
            ParameterSnapshot.t == 0,
        )
        .one_or_none()   # ✅ FIX
    )

    if not snapshot:
        raise HTTPException(
            status_code=500,
            detail="Parameter snapshot missing for project",
        )

    snapshot.payload_json = body.params

    if body.action == "publish":
        project.is_published = True
        project.status = "published"
        project.published_at = func.now()

    db.commit()
    return {"status": "ok"}
