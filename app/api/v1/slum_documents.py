#app/api/v1/slum_documents.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_document import SlumDocument

router = APIRouter(prefix="/slum/documents")

PORTAL_ROLES = {
    "SLUM_DWELLER",
    "AFFORDABLE_HOUSING_DEV",
    "SLUM_LAND_DEVELOPER",
}


def resolve_target_participant(
    principal: Principal, participantId: str | None
) -> str:
    if participantId:
        # Only authority (non-portal roles) can view others
        if principal.role in PORTAL_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Not allowed to access other participant data",
            )
        # validate UUID format but keep as string
        try:
            uuid.UUID(participantId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid participantId")
        return participantId

    return principal.participant_id  # already string


@router.post("/upload")
def upload_document(
    projectId: str = Query(...),
    portalType: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    doc = SlumDocument(
        workflow="slum",
        project_id=pid,
        participant_id=principal.participant_id,
        portal_type=portalType,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
    )

    db.add(doc)
    db.commit()

    return {"status": "uploaded", "filename": file.filename}


@router.get("")
def list_documents(
    projectId: str = Query(...),
    portalType: str = Query(...),
    participantId: str | None = Query(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId")

    target_participant = resolve_target_participant(principal, participantId)

    docs = (
        db.query(SlumDocument)
        .filter(
            SlumDocument.workflow == "slum",
            SlumDocument.project_id == pid,
            SlumDocument.portal_type == portalType,
            SlumDocument.participant_id == target_participant,
        )
        .order_by(SlumDocument.created_at.desc())
        .all()
    )

    return [
        {
            "filename": d.filename,
            "content_type": d.content_type,
            "created_at": d.created_at,
        }
        for d in docs
    ]
