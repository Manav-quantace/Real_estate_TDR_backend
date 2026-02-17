# app/services/unit_inventory_service.py
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.unit_inventory import UnitInventory


class UnitInventoryService:
    def _require_round(self, db: Session, round_id: uuid.UUID) -> Round:
        rnd = db.execute(select(Round).where(Round.id == round_id)).scalar_one_or_none()
        if not rnd:
            raise ValueError("Round not found.")
        return rnd

    def get_for_round(
        self,
        db: Session,
        *,
        round_id: uuid.UUID,
    ) -> Optional[UnitInventory]:
        return db.execute(
            select(UnitInventory).where(UnitInventory.round_id == round_id)
        ).scalar_one_or_none()

    def upsert_for_round(
        self,
        db: Session,
        *,
        round_id: uuid.UUID,
        lu: Optional[Decimal],
        tdru: Optional[Decimal],
        pru: Optional[Decimal],
        dcu: Optional[Decimal],
    ) -> UnitInventory:
        rnd = self._require_round(db, round_id)

        if rnd.is_locked:
            raise ValueError("Cannot modify inventory after round is locked.")

        inv = self.get_for_round(db, round_id=round_id)

        if not inv:
            inv = UnitInventory(
                workflow=rnd.workflow,
                project_id=rnd.project_id,
                round_id=round_id,
                lu=lu,
                tdru=tdru,
                pru=pru,
                dcu=dcu,
            )
            db.add(inv)
        else:
            inv.lu = lu
            inv.tdru = tdru
            inv.pru = pru
            inv.dcu = dcu

        db.commit()
        db.refresh(inv)
        return inv
