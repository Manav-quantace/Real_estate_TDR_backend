from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.hashing import canonical_dumps, sha256_hex
from app.models.audit_log import AuditLogRecord
from app.models.audit_log import AuditLog


class AuditAction:
    # Parameters publish / init snapshots
    PARAMS_PUBLISHED = "PARAMS_PUBLISHED"
    PARAMS_INIT_READ = "PARAMS_INIT_READ"

    # Bids
    BID_SUBMITTED_QUOTE = "BID_SUBMITTED_QUOTE"
    BID_SUBMITTED_ASK = "BID_SUBMITTED_ASK"
    BID_SUBMITTED_PREFERENCES = "BID_SUBMITTED_PREFERENCES"

    # Round lifecycle
    ROUND_OPENED = "ROUND_OPENED"
    ROUND_CLOSED = "ROUND_CLOSED"
    ROUND_LOCKED = "ROUND_LOCKED"

    # Compute engines
    MATCHING_RUN = "MATCHING_RUN"
    SETTLEMENT_RUN = "SETTLEMENT_RUN"

    # Default/penalty/compensatory
    PENALTY_ASSESSED = "PENALTY_ASSESSED"
    OBLIGATION_TRANSFER_BUYER = "OBLIGATION_TRANSFER_BUYER"
    OBLIGATION_TRANSFER_DEVELOPER = "OBLIGATION_TRANSFER_DEVELOPER"

    # Contracts
    CONTRACT_CREATED = "CONTRACT_CREATED"


class AuditService:
    def write(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: str,
        t: Optional[int],
        actor_participant_id: Optional[str],
        action: str,
        request_id: Optional[str],
        details: Dict[str, Any],
    ) -> None:
        row = AuditLog(
            workflow=workflow,
            project_id=project_id,
            t=t,
            actor_participant_id=actor_participant_id,
            action=action,
            request_id=request_id,
            details_json=details,
        )
        db.add(row)
        db.commit()

def _payload_hash(payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_dumps(payload))


def audit_event(
    db: Session,
    *,
    request: Request,
    actor_participant_id: str,
    actor_role: str,
    workflow: str,
    project_id: uuid.UUID,
    t: Optional[int],
    action: str,
    payload_summary: Dict[str, Any],
    status: str = "ok",
    ref_id: Optional[str] = None,
) -> AuditLogRecord:
    """
    Append-only audit record insert.

    payload_summary MUST be safe: do not include other participants' bid amounts.
    Store any sensitive/full payload outside audit log; audit stores hash + safe summary only.
    """
    rid = getattr(request.state, "request_id", None) or "missing"
    route = str(request.url.path)
    method = request.method

    payload_hash = _payload_hash(payload_summary)

    row = AuditLogRecord(
        request_id=rid,
        route=route,
        method=method,
        actor_participant_id=actor_participant_id,
        actor_role=actor_role,
        workflow=workflow,
        project_id=project_id,
        t=t,
        action=action,
        status=status,
        payload_hash=payload_hash,
        payload_summary_json=payload_summary,
        ref_id=ref_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


###major change affected by part19 check 