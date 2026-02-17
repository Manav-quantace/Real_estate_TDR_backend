from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKeyRecord


def stable_hash(payload: Dict[str, Any]) -> str:
    # Deterministic hash for request payload
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class IdempotencyService:
    def get_existing(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        participant_id: str,
        endpoint_key: str,
        idem_key: str,
    ) -> Optional[IdempotencyKeyRecord]:
        return db.execute(
            select(IdempotencyKeyRecord).where(
                IdempotencyKeyRecord.workflow == workflow,
                IdempotencyKeyRecord.project_id == project_id,
                IdempotencyKeyRecord.participant_id == participant_id,
                IdempotencyKeyRecord.endpoint_key == endpoint_key,
                IdempotencyKeyRecord.idem_key == idem_key,
            )
        ).scalar_one_or_none()

    def reserve_or_replay(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        participant_id: str,
        endpoint_key: str,
        idem_key: str,
        request_payload: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int], str]:
        """
        Returns (replay_json, replay_status_code, request_hash).
        If existing record exists:
          - If request_hash matches => replay response
          - If request_hash differs => conflict
        """
        req_hash = stable_hash(request_payload)
        existing = self.get_existing(
            db,
            workflow=workflow,
            project_id=project_id,
            participant_id=participant_id,
            endpoint_key=endpoint_key,
            idem_key=idem_key,
        )
        if not existing:
            return None, None, req_hash

        if existing.request_hash != req_hash:
            raise ValueError("Idempotency-Key reuse with different payload is not allowed.")
        # replay
        return existing.response_json, int(existing.response_status), req_hash

    def store_response(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        participant_id: str,
        endpoint_key: str,
        idem_key: str,
        request_hash: str,
        response_json: Dict[str, Any],
        response_status: int,
    ) -> None:
        existing = self.get_existing(
            db,
            workflow=workflow,
            project_id=project_id,
            participant_id=participant_id,
            endpoint_key=endpoint_key,
            idem_key=idem_key,
        )
        if existing:
            # already stored (or replayed). Do not overwrite.
            return

        row = IdempotencyKeyRecord(
            workflow=workflow,
            project_id=project_id,
            participant_id=participant_id,
            endpoint_key=endpoint_key,
            idem_key=idem_key,
            request_hash=request_hash,
            response_status=str(response_status),
            response_json=response_json,
        )
        db.add(row)
        db.commit()