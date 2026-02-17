from __future__ import annotations

import uuid
from typing import Dict, Any

from sqlalchemy import select, func, cast, Numeric
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.quote_bid import QuoteBid
from app.models.ask_bid import AskBid
from app.models.preference_bid import PreferenceBid


class FeedbackService:
    def get_round(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Round | None:
        return db.execute(
            select(Round).where(
                Round.workflow == workflow, Round.project_id == project_id, Round.t == t
            )
        ).scalar_one_or_none()

    def user_submission_flags(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
    ) -> Dict[str, bool]:
        # booleans only; do not return bid ids
        q = db.execute(
            select(func.count())
            .select_from(QuoteBid)
            .where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.participant_id == participant_id,
                QuoteBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        a = db.execute(
            select(func.count())
            .select_from(AskBid)
            .where(
                AskBid.workflow == workflow,
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.participant_id == participant_id,
                AskBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        p = db.execute(
            select(func.count())
            .select_from(PreferenceBid)
            .where(
                PreferenceBid.workflow == workflow,
                PreferenceBid.project_id == project_id,
                PreferenceBid.t == t,
                PreferenceBid.participant_id == participant_id,
                PreferenceBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        return {
            "user_submitted_quote": bool(q and q > 0),
            "user_submitted_ask": bool(a and a > 0),
            "user_submitted_preferences": bool(p and p > 0),
        }

    def aggregate_stats(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Dict[str, Any]:
        """
        Aggregated counts and min/max ranges only.
        No bid IDs, no payload, no participant fields.
        """
        # Quote: qbundle stored inside payload_json in Part 9 (qbundle_inr field)
        # We'll aggregate via JSONB ->> 'qbundle_inr' cast numeric.
        quote_cnt = db.execute(
            select(func.count())
            .select_from(QuoteBid)
            .where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        quote_minmax = db.execute(
            select(
                func.min(
                    cast(QuoteBid.payload_json["qbundle_inr"].astext, Numeric(20, 2))
                ),
                func.max(
                    cast(QuoteBid.payload_json["qbundle_inr"].astext, Numeric(20, 2))
                ),
            ).where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state.in_(["submitted", "locked"]),
                QuoteBid.payload_json.has_key("qbundle_inr"),
            )
        ).one()

        # Ask: we have separate columns total_ask_inr + compensatory_ask_price_per_unit_inr
        ask_cnt = db.execute(
            select(func.count())
            .select_from(AskBid)
            .where(
                AskBid.workflow == workflow,
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        ask_minmax = db.execute(
            select(
                func.min(AskBid.total_ask_inr),
                func.max(AskBid.total_ask_inr),
                func.min(AskBid.comp_ask_price_per_unit_inr),
                func.max(AskBid.comp_ask_price_per_unit_inr),
            ).where(
                AskBid.workflow == workflow,
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state.in_(["submitted", "locked"]),
            )
        ).one()

        # Preference: count only (no min/max)
        pref_cnt = db.execute(
            select(func.count())
            .select_from(PreferenceBid)
            .where(
                PreferenceBid.workflow == workflow,
                PreferenceBid.project_id == project_id,
                PreferenceBid.t == t,
                PreferenceBid.state.in_(["submitted", "locked"]),
            )
        ).scalar_one()

        # Convert decimals to strings safely
        def s(x):
            return str(x) if x is not None else None

        qmin, qmax = quote_minmax[0], quote_minmax[1]
        amin, amax, cmin, cmax = (
            ask_minmax[0],
            ask_minmax[1],
            ask_minmax[2],
            ask_minmax[3],
        )

        return {
            "quote": {
                "count_total": int(quote_cnt or 0),
                "qbundle_min_inr": s(qmin),
                "qbundle_max_inr": s(qmax),
            },
            "ask": {
                "count_total": int(ask_cnt or 0),
                "total_min_inr": s(amin),
                "total_max_inr": s(amax),
                "comp_ppu_min_inr": s(cmin),
                "comp_ppu_max_inr": s(cmax),
            },
            "preferences": {
                "count_total": int(pref_cnt or 0),
            },
        }
