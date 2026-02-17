from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import uuid

from app.db.session import get_db
from app.models.slum_portal_membership import SlumPortalMembership
from app.core.auth_deps import get_current_principal

router = APIRouter(prefix="/slum/participants")


@router.get("/count")
def get_participant_count(
    projectId: str = Query(...),
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        return {"count": 0}

    count = db.execute(
        select(func.count())
        .select_from(SlumPortalMembership)
        .where(SlumPortalMembership.project_id == pid)
    ).scalar()

    return {"count": count}
