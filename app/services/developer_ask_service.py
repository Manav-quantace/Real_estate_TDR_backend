from sqlalchemy.orm import Session
from app.models.ask_bid import AskBid
from app.models.round import Round
from app.models.bid_enums import BidState
from datetime import datetime


def get_current_round(db: Session, workflow: str, project_id):
    return (
        db.query(Round)
        .filter(
            Round.workflow == workflow,
            Round.project_id == project_id,
            Round.is_open.is_(True),
            Round.is_locked.is_(False),
        )
        .order_by(Round.t.desc())
        .first()
    )


def compute_total_ask(dcu_units: float, price: float) -> float:
    return float(dcu_units) * float(price)


def upsert_ask_bid(
    db: Session,
    *,
    workflow: str,
    project_id,
    participant_id: str,
    dcu_units: float,
    ask_price_per_unit_inr: float,
    action: str,
):
    round_ = get_current_round(db, workflow, project_id)
    if not round_:
        raise ValueError("No open round")

    ask = (
        db.query(AskBid)
        .filter_by(
            workflow=workflow,
            project_id=project_id,
            t=round_.t,
            participant_id=participant_id,
        )
        .first()
    )

    if ask and ask.state == BidState.locked.value:
        raise ValueError("Ask is locked")

    total = compute_total_ask(dcu_units, ask_price_per_unit_inr)

    if not ask:
        ask = AskBid(
            workflow=workflow,
            project_id=project_id,
            round_id=round_.id,
            t=round_.t,
            participant_id=participant_id,
        )
        db.add(ask)

    ask.dcu_units = dcu_units
    ask.ask_price_per_unit_inr = ask_price_per_unit_inr
    ask.total_ask_inr = total

    if action == "submit":
        ask.state = BidState.submitted.value
        ask.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(ask)
    return ask
