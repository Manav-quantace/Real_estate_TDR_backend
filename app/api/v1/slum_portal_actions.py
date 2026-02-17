# app/api/v1/slum_portal_actions.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.models.slum_portal_membership import SlumPortalMembership
from app.models.project import Project
from app.core.slum_types import SlumPortalType

router = APIRouter(prefix="/slum")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _now():
    return datetime.utcnow().isoformat()


def _load_membership(
    db: Session,
    project_id: uuid.UUID,
    participant_id: str,
    portal_type: str,
):
    return db.execute(
        select(SlumPortalMembership).where(
            SlumPortalMembership.workflow == "slum",
            SlumPortalMembership.project_id == project_id,
            SlumPortalMembership.participant_id == participant_id,
            SlumPortalMembership.portal_type == portal_type,
        )
    ).scalar_one_or_none()


# ─────────────────────────────────────────────
# DASHBOARD (participant view)
# ─────────────────────────────────────────────


@router.get("/portal/dashboard")
def portal_dashboard(
    projectId: str,
    portalType: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    try:
        portal = SlumPortalType(portalType)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid portalType.")

    proj = db.execute(
        select(Project).where(Project.workflow == "slum", Project.id == pid)
    ).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")

    membership = _load_membership(db, pid, principal.participant_id, portal.value)
    if not membership:
        raise HTTPException(status_code=403, detail="Not enrolled in this portal.")

    meta = membership.metadata_json or {}

    return {
        "workflow": "slum",
        "projectId": projectId,
        "portalType": portal.value,
        "member": True,
        "consent": meta.get("consent"),
        "documents": meta.get("documents", []),
        "meta": meta,
    }


# ─────────────────────────────────────────────
# CONSENT SUBMISSION
# ─────────────────────────────────────────────


@router.post("/portal/consent")
def submit_consent(
    projectId: str,
    portalType: str,
    consent: bool,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    try:
        portal = SlumPortalType(portalType)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid portalType.")

    membership = _load_membership(db, pid, principal.participant_id, portal.value)
    if not membership:
        raise HTTPException(status_code=403, detail="Not enrolled in this portal.")

    meta = membership.metadata_json or {}

    meta["consent"] = {
        "value": consent,
        "note": note,
        "submitted_at": _now(),
    }

    membership.metadata_json = meta
    db.commit()

    return {"status": "consent_recorded", "consent": meta["consent"]}


# ─────────────────────────────────────────────
# DOCUMENT REGISTER (metadata only)
# ─────────────────────────────────────────────


@router.post("/portal/documents")
def register_document(
    projectId: str,
    portalType: str,
    name: str,
    url: str,
    docType: Optional[str] = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    try:
        portal = SlumPortalType(portalType)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid portalType.")

    membership = _load_membership(db, pid, principal.participant_id, portal.value)
    if not membership:
        raise HTTPException(status_code=403, detail="Not enrolled in this portal.")

    meta = membership.metadata_json or {}
    docs = meta.get("documents", [])

    doc = {
        "name": name,
        "url": url,
        "type": docType,
        "uploaded_at": _now(),
    }

    docs.append(doc)
    meta["documents"] = docs
    membership.metadata_json = meta

    db.commit()

    return {"status": "document_registered", "document": doc}
