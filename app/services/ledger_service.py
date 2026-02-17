#app/services/ledger_service.py
from __future__ import annotations

import uuid
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.contract_ledger import ContractLedgerEntry


def _now():
    return datetime.now(timezone.utc)


def _canonical_json(payload: Dict[str, Any]) -> str:
    """
    Canonical JSON representation:
    - sorted keys
    - no whitespace
    - deterministic string
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    """
    entry_hash = SHA256(prev_hash + canonical(payload))
    """
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(_canonical_json(payload).encode("utf-8"))
    return h.hexdigest()


class LedgerService:
    """
    Append-only contract ledger.
    This is the economic source of truth.
    """

    GENESIS_HASH = "0" * 64

    # ─────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────

    def _get_last_entry(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
    ) -> Optional[ContractLedgerEntry]:
        return db.execute(
            select(ContractLedgerEntry)
            .where(
                ContractLedgerEntry.workflow == workflow,
                ContractLedgerEntry.project_id == project_id,
            )
            .order_by(ContractLedgerEntry.seq.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _next_seq(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
    ) -> int:
        last = self._get_last_entry(db, workflow=workflow, project_id=project_id)
        return 1 if not last else last.seq + 1

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────

    def append_entry(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        contract_id: uuid.UUID,
        entry_type: str,
        payload: Dict[str, Any],
    ) -> ContractLedgerEntry:
        """
        Append a single immutable ledger entry.

        This method is:
        - append-only
        - hash-chained
        - deterministic
        """

        last = self._get_last_entry(db, workflow=workflow, project_id=project_id)

        prev_hash = last.entry_hash if last else self.GENESIS_HASH
        seq = self._next_seq(db, workflow=workflow, project_id=project_id)

        entry_payload = {
            "workflow": workflow,
            "project_id": str(project_id),
            "contract_id": str(contract_id),
            "entry_type": entry_type,
            "payload": payload,
            "created_at": _now().isoformat(),
        }

        entry_hash = _hash(prev_hash, entry_payload)

        row = ContractLedgerEntry(
            workflow=workflow,
            project_id=project_id,
            contract_id=contract_id,
            seq=seq,
            entry_type=entry_type,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            payload_json=entry_payload,
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return row

    # ─────────────────────────────────────────────
    # READ-ONLY HELPERS (AUDIT)
    # ─────────────────────────────────────────────

    def list_entries(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
    ) -> list[ContractLedgerEntry]:
        return (
            db.execute(
                select(ContractLedgerEntry)
                .where(
                    ContractLedgerEntry.workflow == workflow,
                    ContractLedgerEntry.project_id == project_id,
                )
                .order_by(ContractLedgerEntry.seq.asc())
            )
            .scalars()
            .all()
        )

    def verify_chain(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
    ) -> bool:
        """
        Verifies the entire hash chain.
        Used by auditors.
        """
        entries = self.list_entries(db, workflow=workflow, project_id=project_id)

        prev_hash = self.GENESIS_HASH

        for e in entries:
            expected = _hash(prev_hash, e.payload_json)
            if e.entry_hash != expected:
                return False
            prev_hash = e.entry_hash

        return True
