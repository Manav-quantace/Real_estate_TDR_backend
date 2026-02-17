from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.project import Project
from app.models.round import Round
from app.models.unit_inventory import UnitInventory
from app.models.government_charge import GovernmentCharge
from app.models.parameter_snapshot import ParameterSnapshot


class ParamsService:
    """
    Published parameter snapshots.
    - If snapshots exist, return them.
    - If they do not exist, create placeholders (structural) from existing Round/Inventory/Charges.
    """

    @staticmethod
    def _iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    def get_or_create_snapshots(
        self,
        db: Session,
        workflow: str,
        project_uuid,
        published_by_participant_id: Optional[str] = None,
    ) -> Tuple[ParameterSnapshot, ParameterSnapshot]:
        # Get t=0 snapshot if present
        t0 = db.execute(
            select(ParameterSnapshot)
            .where(ParameterSnapshot.workflow == workflow, ParameterSnapshot.project_id == project_uuid, ParameterSnapshot.t == 0)
        ).scalar_one_or_none()

        # Find current round = highest t
        current_round = db.execute(
            select(Round)
            .where(Round.workflow == workflow, Round.project_id == project_uuid)
            .order_by(desc(Round.t))
        ).scalar_one_or_none()

        current_t = current_round.t if current_round else 0

        current = db.execute(
            select(ParameterSnapshot)
            .where(ParameterSnapshot.workflow == workflow, ParameterSnapshot.project_id == project_uuid, ParameterSnapshot.t == current_t)
        ).scalar_one_or_none()

        if not t0:
            t0 = self._create_snapshot_from_state(db, workflow, project_uuid, t=0, published_by_participant_id=published_by_participant_id)

        if not current:
            current = self._create_snapshot_from_state(
                db,
                workflow,
                project_uuid,
                t=current_t,
                published_by_participant_id=published_by_participant_id,
            )

        return t0, current

    def _create_snapshot_from_state(
        self,
        db: Session,
        workflow: str,
        project_uuid,
        t: int,
        published_by_participant_id: Optional[str],
    ) -> ParameterSnapshot:
        # Round t (may not exist yet)
        rnd = db.execute(
            select(Round).where(Round.workflow == workflow, Round.project_id == project_uuid, Round.t == t)
        ).scalar_one_or_none()

        # Inventory snapshot for that round (may not exist)
        inv = None
        if rnd:
            inv = db.execute(
                select(UnitInventory)
                .where(UnitInventory.workflow == workflow, UnitInventory.project_id == project_uuid, UnitInventory.round_id == rnd.id)
            ).scalar_one_or_none()

        # Charges for that round (may not exist)
        charges = []
        if rnd:
            charges = list(
                db.execute(
                    select(GovernmentCharge)
                    .where(GovernmentCharge.workflow == workflow, GovernmentCharge.project_id == project_uuid, GovernmentCharge.round_id == rnd.id)
                ).scalars().all()
            )

        payload: Dict[str, Any] = {
            "workflow": workflow,
            "projectId": str(project_uuid),
            "t": t,
            "round": {
                "t": t,
                "state": getattr(rnd, "state", "draft") if rnd else "draft",
                "bidding_window_start": self._iso(getattr(rnd, "bidding_window_start", None)) if rnd else None,
                "bidding_window_end": self._iso(getattr(rnd, "bidding_window_end", None)) if rnd else None,
                "is_open": (getattr(rnd, "is_open", "false") == "true") if rnd else False,
                "is_locked": (getattr(rnd, "is_locked", "false") == "true") if rnd else False,
            },
            "inventory": {
                "LU": str(inv.lu) if inv and inv.lu is not None else None,
                "TDRU": str(inv.tdru) if inv and inv.tdru is not None else None,
                "PRU": str(inv.pru) if inv and inv.pru is not None else None,
                "DCU": str(inv.dcu) if inv and inv.dcu is not None else None,
            },
            "government_charges": self._charges_payload(charges),
        }

        snap = ParameterSnapshot(
            workflow=workflow,
            project_id=project_uuid,
            t=t,
            payload_json=payload,
            published_by_participant_id=published_by_participant_id,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap

    def _charges_payload(self, charges: list[GovernmentCharge]) -> Dict[str, Any]:
        # Build placeholders even when missing
        out: Dict[str, Any] = {
            "GC": None,
            "GCU": None,
        }
        for c in charges:
            out[c.charge_type] = {
                "weights": c.weights_json,
                "inputs": c.inputs_json,
                "value_inr": str(c.value_inr) if c.value_inr is not None else None,
            }
        return out
