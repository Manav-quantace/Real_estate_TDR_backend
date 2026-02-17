#app/services/preferences_service.py
from __future__ import annotations
import uuid
from typing import Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.preference_bid import PreferenceBid
from app.services.bids_service import BidService


class PreferencesService:
    def __init__(self):
        self.core = BidService()

    def submit_preference(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: Dict[str, Any],
    ) -> PreferenceBid:
        return self.core.submit_preference(db, workflow, project_id, t, participant_id, payload)

    def get_my_preference(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
    ) -> Optional[PreferenceBid]:
        return db.execute(
            select(PreferenceBid).where(
                PreferenceBid.workflow == workflow,
                PreferenceBid.project_id == project_id,
                PreferenceBid.t == t,
                PreferenceBid.participant_id == participant_id,
            )
        ).scalar_one_or_none()

    def save_preference_draft(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: dict,
    ) -> PreferenceBid:
        row = db.execute(
            select(PreferenceBid).where(
                PreferenceBid.workflow == workflow,
                PreferenceBid.project_id == project_id,
                PreferenceBid.t == t,
                PreferenceBid.participant_id == participant_id,
            )
        ).scalar_one_or_none()

        if row and row.state != "draft":
            raise ValueError("Cannot modify non-draft preference.")

        if not row:
            row = PreferenceBid(
                workflow=workflow,
                project_id=project_id,
                t=t,
                participant_id=participant_id,
                payload_json=payload,
                state="draft",
            )
            db.add(row)
        else:
            row.payload_json = payload

        db.commit()
        db.refresh(row)
        return row