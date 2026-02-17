#app/services/government_charge_service.py
from __future__ import annotations

import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.government_charge import GovernmentCharge
from app.models.government_charge_history import GovernmentChargeHistory
from app.models.round import Round


class GovernmentChargeService:
    def _require_round(self, db: Session, round_id: uuid.UUID) -> Round:
        rnd = db.query(Round).filter(Round.id == round_id).first()
        if not rnd:
            raise ValueError("Round not found.")
        if rnd.is_locked:
            raise ValueError("Government charges cannot be modified after round lock.")
        return rnd

    def get(
        self,
        db: Session,
        *,
        round_id: uuid.UUID,
        charge_type: str,
    ) -> Optional[GovernmentCharge]:
        return (
            db.query(GovernmentCharge)
            .filter_by(round_id=round_id, charge_type=charge_type)
            .first()
        )

    def upsert(
        self,
        db: Session,
        *,
        round_id: uuid.UUID,
        charge_type: str,
        weights: Dict[str, Any],
        inputs: Dict[str, Any],
        value_inr: Optional[float],
        actor_participant_id: str,
    ) -> GovernmentCharge:
        rnd = self._require_round(db, round_id)

        existing = self.get(db, round_id=round_id, charge_type=charge_type)

        # ⏺ history snapshot if replacing
        if existing:
            hist = GovernmentChargeHistory(
                charge_id=existing.id,
                workflow=existing.workflow,
                project_id=existing.project_id,
                round_id=existing.round_id,
                charge_type=existing.charge_type,
                weights_json=existing.weights_json,
                inputs_json=existing.inputs_json,
                value_inr=existing.value_inr,
                replaced_by_participant_id=actor_participant_id,
            )
            db.add(hist)

            existing.weights_json = weights
            existing.inputs_json = inputs
            existing.value_inr = value_inr
            db.add(existing)
        else:
            existing = GovernmentCharge(
                workflow=rnd.workflow,
                project_id=rnd.project_id,
                round_id=round_id,
                charge_type=charge_type,
                weights_json=weights,
                inputs_json=inputs,
                value_inr=value_inr,
            )
            db.add(existing)

        db.commit()
        db.refresh(existing)
        return existing

    def history(
        self,
        db: Session,
        *,
        round_id: uuid.UUID,
        charge_type: str,
        limit: int = 50,
    ):
        return (
            db.query(GovernmentChargeHistory)
            .filter_by(round_id=round_id, charge_type=charge_type)
            .order_by(GovernmentChargeHistory.replaced_at.desc())
            .limit(limit)
            .all()
        )
