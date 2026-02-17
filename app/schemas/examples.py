from __future__ import annotations

from decimal import Decimal

from app.schemas.bids import QuoteBidPayload, AskBidPayload, TripartitePreferencePayload
from app.schemas.results import MatchingResult, SettlementResult, SettlementReceipt
from app.schemas.events import PenaltyEvent, CompensatoryEvent
from app.schemas.ledger import (
    TokenizedContractRecord,
    ImmutableEventLog,
    AuditLogRecord,
)
from app.schemas.primitives import BidRound
from app.core.types import WorkflowType


EXAMPLE_QUOTE = QuoteBidPayload(
    workflow=WorkflowType.saleable,
    projectId="PRJ-1",
    t=0,
    qbundle_inr=Decimal("1000000.00"),
    bid_validity_iso="2025-12-13T10:00:00Z",
)

EXAMPLE_ASK_DCU = AskBidPayload(
    workflow=WorkflowType.clearland,
    projectId="PRJ-CL-1",
    t=0,
    dcu_units=Decimal("100.0000"),
    ask_price_per_unit_inr=Decimal("50000.00"),
    bid_validity_iso="2025-12-13T10:00:00Z",
)

EXAMPLE_PREF = TripartitePreferencePayload(
    workflow=WorkflowType.slum,
    projectId="PRJ-SL-1",
    t=0,
    rehab_option="Option-A",
    household_details={"members": 4, "id_doc": "AADHAAR_MASKED"},
    consent={"targeting": True, "data_share": False},
)

EXAMPLE_ROUND = BidRound(
    t=0,
    state="draft",
    bidding_window_start="2025-12-13T09:00:00Z",
    bidding_window_end="2025-12-13T18:00:00Z",
    is_open=True,
    is_locked=False,
)

EXAMPLE_MATCHING = MatchingResult(
    workflow=WorkflowType.slum,
    projectId="PRJ-SL-1",
    t=0,
    round=EXAMPLE_ROUND,
    status="MATCHED",
    summary={"tripartite": True},
    matched_entities=["P-DEV-001", "P-AH-001", "P-SD-001"],
)

EXAMPLE_SETTLEMENT = SettlementResult(
    workflow=WorkflowType.clearland,
    projectId="PRJ-CL-1",
    t=0,
    round=EXAMPLE_ROUND,
    status="READY",
    winners=[{"winner_bid_id": "BID-001", "winner": "P-BUY-001"}],
    second_price_payments=[{"paid_by": "P-BUY-001", "amount_inr": "8500000.00"}],
    receipts=[
        SettlementReceipt(receipt_id="RCT-001", amount_inr=Decimal("8500000.00"))
    ],
    audit_link="/v1/ledger/audit?workflow=clearland&projectId=PRJ-CL-1&t=0",
)

EXAMPLE_PENALTY = PenaltyEvent(
    workflow=WorkflowType.clearland,
    projectId="PRJ-CL-1",
    t=0,
    event_id="PE-001",
    status="ASSESSED",
    winner_bid_id="BID-001",
    second_bid_id="BID-002",
    penalty_amount_inr=Decimal("100000.00"),
)

EXAMPLE_COMP = CompensatoryEvent(
    workflow=WorkflowType.clearland,
    projectId="PRJ-CL-1",
    t=0,
    event_id="CE-001",
    status="RESOLVED",
    original_winner_bid_id="BID-001",
    reassigned_to_bid_id="BID-002",
    constraint_applied={"b_second_new_lte_b_second": True},
)

EXAMPLE_CONTRACT = TokenizedContractRecord(
    workflow=WorkflowType.saleable,
    projectId="PRJ-1",
    contract_id="CTR-SALEABLE-PRJ-1",
    version="1.0",
    published_at_iso="2025-12-13T12:00:00Z",
    ownership_details={"owner": "Society-XYZ"},
    transaction_data={"settlement_receipt": "RCT-001"},
    obligations=[{"party": "developer", "text": "Complete redevelopment timeline"}],
    immutable_event_logs=[
        ImmutableEventLog(
            event_id="EVT-1",
            timestamp_iso="2025-12-13T12:00:00Z",
            event_type="CONTRACT_TOKENIZED",
            actor="exchange",
            ref={"receipt_id": "RCT-001"},
        )
    ],
    links={"audit": "/v1/ledger/audit?workflow=saleable&projectId=PRJ-1"},
)

EXAMPLE_AUDIT = AuditLogRecord(
    workflow=WorkflowType.saleable,
    projectId="PRJ-1",
    audit_id="AUD-001",
    timestamp_iso="2025-12-13T12:00:01Z",
    actor="exchange",
    action="SETTLEMENT_PUBLISHED",
    t=0,
    request_id="req-123",
    payload_hash="hash-abc",
    details={"note": "structural example"},
)
