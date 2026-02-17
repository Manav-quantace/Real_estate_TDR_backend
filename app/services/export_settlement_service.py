from __future__ import annotations

import uuid
from typing import Dict, Any, Iterable, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.settlement_result import SettlementResult  # Part 14
from app.policies.export_policy import ExportScope


SETTLEMENT_FIELDS = [
    "settlement_result_id", "workflow", "project_id", "t",
    "created_at",
    "winning_quote_bid_id", "winning_ask_bid_id",
    "second_price_reference",
    "winner_participant_id",
]


class ExportSettlementService:
    def iter_rows(
        self,
        db: Session,
        *,
        scope: ExportScope,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Iterable[Dict[str, Any]]:
        stmt = select(SettlementResult).where(
            SettlementResult.workflow == workflow,
            SettlementResult.project_id == project_id,
            SettlementResult.t == t,
        )
        rows = db.execute(stmt).scalars().all()

        for r in rows:
            winner_pid = getattr(r, "winner_participant_id", None) or (r.public_json or {}).get("winner_participant_id")
            if not scope.allow_full:
                # participant must match winner to see the row
                if winner_pid != scope.participant_id:
                    continue

            # second-price stored explicitly (as required in Part 14)
            second_ref = getattr(r, "second_price_reference_json", None) or getattr(r, "second_price_reference", None) or (r.public_json or {}).get("second_price_reference")

            yield {
                "settlement_result_id": str(r.id),
                "workflow": r.workflow,
                "project_id": str(r.project_id),
                "t": r.t,
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
                "winning_quote_bid_id": str(r.winning_quote_bid_id) if getattr(r, "winning_quote_bid_id", None) else None,
                "winning_ask_bid_id": str(r.winning_ask_bid_id) if getattr(r, "winning_ask_bid_id", None) else None,
                "second_price_reference": str(second_ref) if second_ref is not None else None,
                "winner_participant_id": winner_pid,
            }

    def fieldnames(self) -> List[str]:
        return SETTLEMENT_FIELDS