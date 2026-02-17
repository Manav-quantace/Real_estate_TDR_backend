#app/services/bids_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Type
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.signing import canonical_hash
from app.models.bid_enums import BidState
from app.models.round import Round
from app.models.quote_bid import QuoteBid
from app.models.ask_bid import AskBid
from app.models.preference_bid import PreferenceBid


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _now():
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    """
    Convert payload into JSON-safe structure.
    REQUIRED for payload_json (Postgres JSON/JSONB).
    """
    if isinstance(value, Decimal):
        return str(value)  # preserve precision
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


# ---------------------------------------------------------------------
# service
# ---------------------------------------------------------------------


class BidService:
    def _get_round(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Round:
        rnd = db.execute(
            select(Round).where(
                Round.workflow == workflow,
                Round.project_id == project_id,
                Round.t == t,
            )
        ).scalar_one_or_none()
        if not rnd:
            raise ValueError("Round not found.")
        return rnd

    def _ensure_round_mutable(self, rnd: Round) -> None:
        if rnd.is_locked:
            raise ValueError(
                "Round is locked; bids are append-only. Submit in next round."
            )
        if not rnd.is_open:
            raise ValueError("Round is closed; bid submissions are not allowed.")

    # -----------------------------------------------------------------
    # drafts
    # -----------------------------------------------------------------

    def _save_draft(
        self,
        db: Session,
        *,
        model: Type[QuoteBid] | Type[AskBid] | Type[PreferenceBid],
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: Dict[str, Any],
    ):
        rnd = self._get_round(db, workflow, project_id, t)
        self._ensure_round_mutable(rnd)

        payload_json = _json_safe(payload)

        row = db.execute(
            select(model).where(
                model.workflow == workflow,
                model.project_id == project_id,
                model.t == t,
                model.participant_id == participant_id,
            )
        ).scalar_one_or_none()

        if row and row.state == BidState.locked.value:
            raise ValueError("Locked bids cannot be updated (append-only).")

        if not row:
            row = model(
                workflow=workflow,
                project_id=project_id,
                round_id=rnd.id,
                t=t,
                participant_id=participant_id,
                state=BidState.draft.value,
                payload_json=payload_json,
            )
            db.add(row)
        else:
            row.payload_json = payload_json
            row.state = BidState.draft.value

        db.commit()
        db.refresh(row)
        return row

    def save_quote_draft(self, db, workflow, project_id, t, participant_id, payload):
        return self._save_draft(
            db,
            model=QuoteBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    def save_ask_draft(self, db, workflow, project_id, t, participant_id, payload):
        return self._save_draft(
            db,
            model=AskBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    def save_preference_draft(
        self, db, workflow, project_id, t, participant_id, payload
    ):
        return self._save_draft(
            db,
            model=PreferenceBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    # -----------------------------------------------------------------
    # submit
    # -----------------------------------------------------------------

    def _submit(
        self,
        db: Session,
        *,
        model: Type[QuoteBid] | Type[AskBid] | Type[PreferenceBid],
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: Dict[str, Any],
    ):
        rnd = self._get_round(db, workflow, project_id, t)
        self._ensure_round_mutable(rnd)

        payload_json = _json_safe(payload)

        row = db.execute(
            select(model).where(
                model.workflow == workflow,
                model.project_id == project_id,
                model.t == t,
                model.participant_id == participant_id,
            )
        ).scalar_one_or_none()

        if row and row.state == BidState.locked.value:
            raise ValueError("Locked bids cannot be updated; submit in next round.")

        if not row:
            row = model(
                workflow=workflow,
                project_id=project_id,
                round_id=rnd.id,
                t=t,
                participant_id=participant_id,
                state=BidState.submitted.value,
                payload_json=payload_json,
                submitted_at=_now(),
            )
            db.add(row)
        else:
            row.payload_json = payload_json
            row.state = BidState.submitted.value
            row.submitted_at = _now()

        db.commit()
        db.refresh(row)
        return row

    def submit_quote(self, db, workflow, project_id, t, participant_id, payload):
        return self._submit(
            db,
            model=QuoteBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    def submit_ask(self, db, workflow, project_id, t, participant_id, payload):
        return self._submit(
            db,
            model=AskBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    def submit_preference(
        self, db, workflow, project_id, t, participant_id, payload
    ):
        return self._submit(
            db,
            model=PreferenceBid,
            workflow=workflow,
            project_id=project_id,
            t=t,
            participant_id=participant_id,
            payload=payload,
        )

    # -----------------------------------------------------------------
    # locking
    # -----------------------------------------------------------------

    def lock_all_bids_for_round(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        actor_participant_id: Optional[str] = None,
    ) -> Dict[str, int]:
        rnd = self._get_round(db, workflow, project_id, t)
        if rnd.is_open:
            raise ValueError("Round must be closed before locking bids.")
        if rnd.is_locked:
            return {"quote": 0, "ask": 0, "preference": 0}

        def lock_rows(model):
            rows = list(
                db.execute(
                    select(model).where(
                        model.workflow == workflow,
                        model.project_id == project_id,
                        model.t == t,
                    )
                )
                .scalars()
                .all()
            )
            n = 0
            for r in rows:
                if r.state != BidState.locked.value:
                    signed = {
                        "workflow": r.workflow,
                        "project_id": str(r.project_id),
                        "t": r.t,
                        "participant_id": r.participant_id,
                        "payload": r.payload_json,
                    }
                    r.signature_hash = canonical_hash(signed)
                    r.state = BidState.locked.value
                    r.locked_at = _now()
                    n += 1
            return n

        qn = lock_rows(QuoteBid)
        an = lock_rows(AskBid)
        pn = lock_rows(PreferenceBid)

        db.commit()
        return {"quote": qn, "ask": an, "preference": pn}
