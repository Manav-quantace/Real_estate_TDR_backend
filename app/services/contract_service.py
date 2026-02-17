from __future__ import annotations

import uuid
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.hashing import canonical_dumps, sha256_hex, hash_chain
from app.models.tokenized_contract import TokenizedContractRecord
from app.models.contract_ledger import ContractLedgerEntry
from app.models.settlement_result import SettlementResult
from app.models.penalty_event import PenaltyEvent
from app.models.compensatory_event import CompensatoryEvent
from app.models.developer_compensatory_event import DeveloperCompensatoryEvent


GENESIS_HASH = "0" * 64


class ContractService:
    def _latest_contract(self, db: Session, workflow: str, project_id: uuid.UUID) -> Optional[TokenizedContractRecord]:
        return db.execute(
            select(TokenizedContractRecord)
            .where(TokenizedContractRecord.workflow == workflow, TokenizedContractRecord.project_id == project_id)
            .order_by(desc(TokenizedContractRecord.version))
            .limit(1)
        ).scalar_one_or_none()

    def _next_seq(self, db: Session, workflow: str, project_id: uuid.UUID) -> int:
        mx = db.execute(
            select(func.max(ContractLedgerEntry.seq))
            .where(ContractLedgerEntry.workflow == workflow, ContractLedgerEntry.project_id == project_id)
        ).scalar_one_or_none()
        return int(mx or 0) + 1

    def _last_hash(self, db: Session, workflow: str, project_id: uuid.UUID) -> str:
        last = db.execute(
            select(ContractLedgerEntry.entry_hash)
            .where(ContractLedgerEntry.workflow == workflow, ContractLedgerEntry.project_id == project_id)
            .order_by(desc(ContractLedgerEntry.seq))
            .limit(1)
        ).scalar_one_or_none()
        return last or GENESIS_HASH

    def _load_settlement(self, db: Session, workflow: str, project_id: uuid.UUID) -> Optional[SettlementResult]:
        # Latest settled settlement result for the project (across t)
        return db.execute(
            select(SettlementResult)
            .where(SettlementResult.workflow == workflow, SettlementResult.project_id == project_id)
            .order_by(desc(SettlementResult.t))
            .limit(1)
        ).scalar_one_or_none()

    def _optional_penalty(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[PenaltyEvent]:
        return db.execute(
            select(PenaltyEvent).where(PenaltyEvent.workflow == workflow, PenaltyEvent.project_id == project_id, PenaltyEvent.t == t)
        ).scalar_one_or_none()

    def _optional_comp(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[CompensatoryEvent]:
        return db.execute(
            select(CompensatoryEvent).where(CompensatoryEvent.workflow == workflow, CompensatoryEvent.project_id == project_id, CompensatoryEvent.t == t)
        ).scalar_one_or_none()

    def _optional_dev_comp(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[DeveloperCompensatoryEvent]:
        return db.execute(
            select(DeveloperCompensatoryEvent).where(
                DeveloperCompensatoryEvent.workflow == workflow,
                DeveloperCompensatoryEvent.project_id == project_id,
                DeveloperCompensatoryEvent.t == t,
            )
        ).scalar_one_or_none()

    def _build_contract_sections(
        self,
        *,
        settlement: SettlementResult,
        penalty: Optional[PenaltyEvent],
        comp: Optional[CompensatoryEvent],
        dev_comp: Optional[DeveloperCompensatoryEvent],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        # Ownership Details: minimal, derived from settlement references (no guessing)
        ownership = {
            "workflow": settlement.workflow,
            "project_id": str(settlement.project_id),
            "round_t": settlement.t,
            "winner_quote_bid_id": str(settlement.winner_quote_bid_id) if settlement.winner_quote_bid_id else None,
            "winning_ask_bid_id": str(settlement.winning_ask_bid_id) if settlement.winning_ask_bid_id else None,
            "note": "Ownership is represented by winning bid references and subsequent ledger events.",
        }

        # Transaction Data: payment references only (no computation)
        txn = {
            "vickrey": {
                "max_quote_inr": str(settlement.max_quote_inr) if settlement.max_quote_inr is not None else None,
                "second_price_inr": str(settlement.second_price_inr) if settlement.second_price_inr is not None else None,
                "second_price_quote_bid_id": str(settlement.second_price_quote_bid_id) if settlement.second_price_quote_bid_id else None,
            },
            "settlement_receipt": settlement.receipt_json or {},
        }

        # Legal Obligations: include penalty/compensatory references (no policy invention)
        obligations: Dict[str, Any] = {
            "default_penalty": None,
            "buyer_compensatory_reallocation": None,
            "developer_compensatory_transfer": None,
            "immutability": "append-only; new versions create new records",
        }

        if penalty:
            obligations["default_penalty"] = {
                "penalty_event_id": str(penalty.id),
                "formula": "Pconfiscation = bmax − bsecond",
                "bmax_inr": str(penalty.bmax_inr),
                "bsecond_inr": str(penalty.bsecond_inr),
                "penalty_inr": str(penalty.penalty_inr),
                "enforcement_status": penalty.enforcement_status,
            }

        if comp:
            obligations["buyer_compensatory_reallocation"] = {
                "compensatory_event_id": str(comp.id),
                "status": comp.status,
                "constraint": "bsecond,new ≤ bsecond",
                "enforcement_action": comp.enforcement_action,
                "bsecond_new_raw_inr": str(comp.bsecond_new_raw_inr) if comp.bsecond_new_raw_inr is not None else None,
                "bsecond_new_enforced_inr": str(comp.bsecond_new_enforced_inr) if comp.bsecond_new_enforced_inr is not None else None,
                "new_winner_quote_bid_id": str(comp.new_winner_quote_bid_id) if comp.new_winner_quote_bid_id else None,
            }

        if dev_comp:
            obligations["developer_compensatory_transfer"] = {
                "developer_comp_event_id": str(dev_comp.id),
                "status": dev_comp.status,
                "original_winning_ask_bid_id": str(dev_comp.original_winning_ask_bid_id),
                "new_winning_ask_bid_id": str(dev_comp.new_winning_ask_bid_id) if dev_comp.new_winning_ask_bid_id else None,
                "compensatory_reference": {
                    "comp_dcu_units": str(dev_comp.comp_dcu_units) if dev_comp.comp_dcu_units is not None else None,
                    "comp_ask_price_per_unit_inr": str(dev_comp.comp_ask_price_per_unit_inr) if dev_comp.comp_ask_price_per_unit_inr is not None else None,
                },
            }

        return ownership, txn, obligations

    def create_or_get_latest_for_project(self, db: Session, *, workflow: str, project_id: uuid.UUID) -> TokenizedContractRecord:
        latest = self._latest_contract(db, workflow, project_id)
        if latest:
            return latest

        settlement = self._load_settlement(db, workflow, project_id)
        if not settlement:
            raise ValueError("No SettlementResult found for project.")
        settled_bool = bool(settlement.settled == "true" if isinstance(settlement.settled, str) else settlement.settled)
        if not settled_bool:
            raise ValueError("SettlementResult not settled; cannot create TokenizedContractRecord.")

        penalty = self._optional_penalty(db, workflow, project_id, settlement.t)
        comp = self._optional_comp(db, workflow, project_id, settlement.t)
        dev_comp = self._optional_dev_comp(db, workflow, project_id, settlement.t)

        ownership, txn, obligations = self._build_contract_sections(
            settlement=settlement, penalty=penalty, comp=comp, dev_comp=dev_comp
        )

        # Contract hash = hash(canonical(full_contract_payload))
        full_payload = {
            "ownership_details": ownership,
            "transaction_data": txn,
            "legal_obligations": obligations,
        }
        contract_hash = sha256_hex(canonical_dumps(full_payload))

        contract = TokenizedContractRecord(
            workflow=workflow,
            project_id=project_id,
            version=1,
            prior_contract_id=None,
            settlement_result_id=settlement.id,
            ownership_details_json=ownership,
            transaction_data_json=txn,
            legal_obligations_json=obligations,
            contract_hash=contract_hash,
        )
        db.add(contract)
        db.flush()  # get id

        # Ledger entry (append-only)
        seq = self._next_seq(db, workflow, project_id)
        prev_hash = self._last_hash(db, workflow, project_id)

        entry_payload = {
            "entry_type": "CONTRACT_CREATED",
            "contract_id": str(contract.id),
            "contract_hash": contract_hash,
            "settlement_result_id": str(settlement.id),
            "round_t": settlement.t,
        }
        entry_hash = hash_chain(prev_hash, entry_payload)

        db.add(ContractLedgerEntry(
            workflow=workflow,
            project_id=project_id,
            contract_id=contract.id,
            seq=seq,
            entry_type="CONTRACT_CREATED",
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            payload_json=entry_payload,
        ))

        db.commit()
        db.refresh(contract)
        return contract

    def get_contract(self, db: Session, contract_id: uuid.UUID) -> Optional[TokenizedContractRecord]:
        return db.execute(select(TokenizedContractRecord).where(TokenizedContractRecord.id == contract_id)).scalar_one_or_none()

    def list_by_project(self, db: Session, *, workflow: str, project_id: uuid.UUID) -> List[TokenizedContractRecord]:
        return db.execute(
            select(TokenizedContractRecord)
            .where(TokenizedContractRecord.workflow == workflow, TokenizedContractRecord.project_id == project_id)
            .order_by(desc(TokenizedContractRecord.version))
        ).scalars().all()
