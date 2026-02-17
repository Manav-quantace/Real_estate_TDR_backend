#app/services/charges_service.py
from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.round import Round
from app.models.government_charge import GovernmentCharge
from app.models.government_charge_history import GovernmentChargeHistory
from app.services.charges_compute import compute_gc, compute_gcu


def _money2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ChargesService:
    def get_round(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[Round]:
        return db.execute(
            select(Round).where(Round.workflow == workflow, Round.project_id == project_id, Round.t == t)
        ).scalar_one_or_none()

    def get_or_create_charge(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        round_id: uuid.UUID,
        charge_type: str,
    ) -> GovernmentCharge:
        row = db.execute(
            select(GovernmentCharge).where(
                GovernmentCharge.workflow == workflow,
                GovernmentCharge.project_id == project_id,
                GovernmentCharge.round_id == round_id,
                GovernmentCharge.charge_type == charge_type,
            )
        ).scalar_one_or_none()

        if row:
            return row

        # Placeholder: empty weights/inputs/value
        row = GovernmentCharge(
            workflow=workflow,
            project_id=project_id,
            round_id=round_id,
            charge_type=charge_type,
            weights_json={},
            inputs_json={},
            value_inr=None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def recalc_charge(
        self,
        db: Session,
        *,
        charge: GovernmentCharge,
        actor_participant_id: Optional[str],
    ) -> GovernmentCharge:
        """
        Recalculate using stored weights_json and inputs_json.
        Preserve history: copy old record to history table, then update current value_inr.
        """
        # 1) push existing into history (even if value_inr None, still preserve state)
        hist = GovernmentChargeHistory(
            charge_id=charge.id,
            workflow=charge.workflow,
            project_id=charge.project_id,
            round_id=charge.round_id,
            charge_type=charge.charge_type,
            weights_json=charge.weights_json or {},
            inputs_json=charge.inputs_json or {},
            value_inr=charge.value_inr,
            replaced_by_participant_id=actor_participant_id,
        )
        db.add(hist)

        # 2) compute new
        if charge.charge_type == "GC":
            val = compute_gc(charge.weights_json or {}, charge.inputs_json or {})
            charge.value_inr = _money2(val)
        elif charge.charge_type == "GCU":
            gcu, pvic, ec = compute_gcu(charge.weights_json or {}, charge.inputs_json or {})
            # store computed components back into inputs_json for traceability (structural)
            updated_inputs = dict(charge.inputs_json or {})
            updated_inputs["PVIC"] = str(_money2(pvic))
            updated_inputs["EC"] = str(_money2(ec))
            charge.inputs_json = updated_inputs
            charge.value_inr = _money2(gcu)
        else:
            raise ValueError("Invalid charge_type")

        db.add(charge)
        db.commit()
        db.refresh(charge)
        return charge