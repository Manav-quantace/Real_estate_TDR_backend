from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, cast, Numeric, desc

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.core.deps_params import require_workflow_project_scope
from app.models.quote_bid import QuoteBid
from app.models.ask_bid import AskBid

router = APIRouter(
    prefix="/authority/settlement/diagnostics",
    tags=["authority"],
)


@router.get(
    "",
    dependencies=[Depends(require_workflow_project_scope)],
)
def settlement_diagnostics(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    """
    Authority-only diagnostics explaining WHY settlement can / cannot occur.
    """

    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Authority only")

    workflow = request.state.workflow
    project_id = uuid.UUID(request.state.project_id)

    # -----------------------
    # QUOTES (LOCKED)
    # -----------------------
    q_val = cast(
        QuoteBid.payload_json["qbundle_inr"].astext,
        Numeric(20, 2),
    )

    locked_quotes = db.execute(
        select(q_val)
        .where(
            QuoteBid.workflow == workflow,
            QuoteBid.project_id == project_id,
            QuoteBid.t == t,
            QuoteBid.state == "locked",
            QuoteBid.payload_json.has_key("qbundle_inr"),
        )
        .order_by(desc(q_val))
    ).scalars().all()

    max_quote = locked_quotes[0] if locked_quotes else None
    second_quote = locked_quotes[1] if len(locked_quotes) > 1 else None

    # -----------------------
    # ASKS (LOCKED)
    # -----------------------
    locked_asks = db.execute(
        select(AskBid)
        .where(
            AskBid.workflow == workflow,
            AskBid.project_id == project_id,
            AskBid.t == t,
            AskBid.state == "locked",
        )
    ).scalars().all()

    ask_totals = [
        a.total_ask_inr
        for a in locked_asks
        if a.total_ask_inr is not None
    ]

    min_ask_total = min(ask_totals) if ask_totals else None

    # -----------------------
    # CONDITIONS
    # -----------------------
    conditions = {
        "has_locked_quotes": len(locked_quotes) > 0,
        "has_locked_asks": len(locked_asks) > 0,
        "has_computable_asks": min_ask_total is not None,
        "has_second_price": second_quote is not None,
        "price_crossed": (
            max_quote is not None
            and min_ask_total is not None
            and min_ask_total <= max_quote
        ),
    }

    can_settle = all(conditions.values())

    return {
        "round": t,
        "quotes": {
            "locked_count": len(locked_quotes),
            "max_quote_inr": str(max_quote) if max_quote else None,
            "second_quote_inr": str(second_quote) if second_quote else None,
        },
        "asks": {
            "locked_count": len(locked_asks),
            "min_ask_total_inr": str(min_ask_total) if min_ask_total else None,
        },
        "settlement_conditions": conditions,
        "can_settle": can_settle,
    }
