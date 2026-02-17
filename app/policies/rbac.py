#app/policies/rbac.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Set

from app.models.enums import ParticipantRole


@dataclass(frozen=True)
class Principal:
    participant_id: str
    workflow: str
    role: ParticipantRole
    display_name: str


# --- Core action constants ---
ACTION_SUBMIT_QUOTE = "SUBMIT_QUOTE"
ACTION_SUBMIT_ASK = "SUBMIT_ASK"
ACTION_SUBMIT_PREFERENCES = "SUBMIT_PREFERENCES"


def allowed_actions(role: ParticipantRole) -> Set[str]:
    """
    Pure RBAC: which actions a role may attempt.
    """

    if role == ParticipantRole.BUYER:
        return {ACTION_SUBMIT_QUOTE}

    if role == ParticipantRole.AFFORDABLE_HOUSING_DEV:
        return {ACTION_SUBMIT_QUOTE}

    if role == ParticipantRole.DEVELOPER:
        return {ACTION_SUBMIT_ASK}

    if role == ParticipantRole.OWNER_SOCIETY:
        return {ACTION_SUBMIT_ASK}

    if role == ParticipantRole.SLUM_DWELLER:
        return {ACTION_SUBMIT_PREFERENCES}

    if role == ParticipantRole.GOV_AUTHORITY:
        return set()

    if role == ParticipantRole.AUDITOR:
        return set()

    return set()


def require_action(principal: Principal, action: str) -> None:
    if action not in allowed_actions(principal.role):
        raise PermissionError(
            f"Role {principal.role.value} not permitted for action {action}."
        )
