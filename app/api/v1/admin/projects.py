from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.models.project import Project
from app.models.enums import ParticipantRole

router = APIRouter(prefix="/admin/projects", tags=["admin"])


@router.get("")
def list_all_projects(
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    if principal.role != ParticipantRole.GOV_AUTHORITY:
        raise HTTPException(status_code=403, detail="Authority only")

    projects = db.query(Project).order_by(Project.created_at.desc()).all()

    return {
        "projects": [
            {
                "projectId": str(p.id),
                "workflow": p.workflow,
                "title": p.title,
                "status": p.status,
                "isPublished": p.is_published,
                "createdAt": p.created_at.isoformat(),
            }
            for p in projects
        ]
    }
