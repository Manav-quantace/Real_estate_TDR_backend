#app/services/quote_bids_service.py
from __future__ import annotations

import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quote_bid import QuoteBid
from app.models.bid_enums import BidState
from app.services.bids_service import BidService


class QuoteBidsService:
    def __init__(self):
        self.core = BidService()

    def submit_quote_bid(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: Dict[str, Any],
    ) -> QuoteBid:
        # Uses Part 8 enforcement: round open + not locked; creates/updates only while mutable
        return self.core.submit_quote(db, workflow, project_id, t, participant_id, payload)

    def get_my_quote_bids(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
    ) -> List[QuoteBid]:
        # Strict: only caller’s bids
        rows = list(
            db.execute(
                select(QuoteBid).where(
                    QuoteBid.workflow == workflow,
                    QuoteBid.project_id == project_id,
                    QuoteBid.t == t,
                    QuoteBid.participant_id == participant_id,
                )
            ).scalars().all()
        )
        return rows