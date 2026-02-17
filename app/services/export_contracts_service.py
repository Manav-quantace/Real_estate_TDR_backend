from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Iterable, Iterator
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, or_

from app.models.tokenized_contract import TokenizedContractRecord  # from Part 18
from app.policies.export_policy import ExportScope


class ExportContractsService:
    def iter_contract_dicts(
        self,
        db: Session,
        *,
        scope: ExportScope,
        workflow: str,
        project_id: uuid.UUID,
        limit: int = 50000,
    ) -> Iterable[Dict[str, Any]]:
        stmt = select(TokenizedContractRecord).where(
            TokenizedContractRecord.workflow == workflow,
            TokenizedContractRecord.project_id == project_id,
        )

        if not scope.allow_full:
            # Fallback participant scoping using typical keys. Adjust keys to your Part 18 record if needed.
            pid = scope.participant_id
            stmt = stmt.where(
                or_(
                    TokenizedContractRecord.ownership_json["participant_id"].astext == pid,
                    TokenizedContractRecord.transaction_json["buyer_participant_id"].astext == pid,
                    TokenizedContractRecord.transaction_json["seller_participant_id"].astext == pid,
                )
            )

        stmt = stmt.order_by(desc(TokenizedContractRecord.created_at)).limit(limit)

        for c in db.execute(stmt).scalars().yield_per(500):
            yield {
                "contractId": str(c.id),
                "workflow": c.workflow,
                "projectId": str(c.project_id),
                "createdAtIso": c.created_at.isoformat() if c.created_at else None,
                "recordHash": c.record_hash,
                "prevHash": c.prev_hash,
                "ownership": c.ownership_json or {},
                "transaction": c.transaction_json or {},
                "obligations": c.obligations_json or {},
                "eventLog": c.event_log_json or [],
            }

    def json_stream(self, contracts: Iterable[Dict[str, Any]]) -> Iterator[bytes]:
        # Stream as a JSON array without buffering the whole set.
        yield b'{"contracts":['
        first = True
        for c in contracts:
            if not first:
                yield b","
            first = False
            yield json.dumps(c, ensure_ascii=False).encode("utf-8")
        yield b"]}"
