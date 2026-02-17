# app/api/v1/developer_ask.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.schemas.ask_bid import AskBidUpsert, DeveloperAskPageOut
from app.services.developer_ask_service import (
    get_current_round,
    upsert_ask_bid,
)
from app.models.ask_bid import AskBid

router = APIRouter(
    prefix="/saleable/projects",
    tags=["developer_ask"],
)


@router.get("/{project_id}/developer-ask", response_model=DeveloperAskPageOut)
def get_developer_ask(
    project_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # Enforce workflow at auth layer
    if principal.workflow != "saleable":
        raise HTTPException(status_code=403, detail="Invalid workflow")

    workflow = "saleable"
    participant_id = principal.participant_id

    round_ = get_current_round(db, workflow, project_id)

    ask = None
    if round_:
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

    return DeveloperAskPageOut(
        project={"id": str(project_id)},
        round={"t": round_.t if round_ else None},
        ask_bid=ask,
    )


@router.post("/{project_id}/developer-ask")
def upsert_developer_ask(
    project_id: UUID,
    payload: AskBidUpsert,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.workflow != "saleable":
        raise HTTPException(status_code=403, detail="Invalid workflow")

    workflow = "saleable"
    participant_id = principal.participant_id

    ask = upsert_ask_bid(
        db,
        workflow=workflow,
        project_id=project_id,
        participant_id=participant_id,
        dcu_units=payload.dcu_units,
        ask_price_per_unit_inr=payload.ask_price_per_unit_inr,
        action=payload.action,
    )

    return {"status": "ok", "ask_id": str(ask.id)}
