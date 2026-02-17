from __future__ import annotations
from typing import Any, Dict

from app.models.enums import ParticipantRole
from app.policies.rbac import Principal


def enforce_ask_payload_no_tdr(principal: Principal, payload: Dict[str, Any]) -> None:
    """
    Developers/builders may submit ASK bids only for DCU (and compensatory DCU), NOT for TDR/LU/PRU.
    """

    if principal.role not in {
        ParticipantRole.DEVELOPER,
        ParticipantRole.OWNER_SOCIETY,
    }:
        return

    forbidden_keys = {
        "tdru", "TDRU", "tdr_units", "ask_tdru", "ask_tdr_price",
        "tdr", "TDR", "pru", "PRU", "lu", "LU",
        "qtdr_inr", "qlu_inr", "qpru_inr",
    }

    present = {k for k in payload.keys() if k in forbidden_keys}
    if present:
        raise PermissionError(
            "Ask bids may only be DCU-based. TDR/LU/PRU not permitted."
        )

    if not any(k in payload for k in ("dcu_units", "DCU_units", "dcu")):
        raise PermissionError("Ask bid must include dcu_units.")


def enforce_preferences_payload_role(principal: Principal) -> None:
    if principal.role != ParticipantRole.SLUM_DWELLER:
        raise PermissionError("Only SLUM_DWELLER may submit preferences.")


def enforce_developer_dcu_only(principal: Principal) -> None:
    """
    Roles allowed to submit ASK bids.
    """
    if principal.role not in {
        ParticipantRole.DEVELOPER,
        ParticipantRole.OWNER_SOCIETY,
    }:
        raise PermissionError("Role not permitted to submit ask bids.")


def enforce_quote_payload_role(principal: Principal) -> None:
    """
    Roles allowed to submit QUOTE bids (Qbundle).
    """
    if principal.role not in {
        ParticipantRole.BUYER,
        ParticipantRole.AFFORDABLE_HOUSING_DEV,
    }:
        raise PermissionError("Role not permitted to submit quote bids.")
