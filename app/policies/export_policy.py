from __future__ import annotations
from dataclasses import dataclass
from app.policies.rbac import Principal


@dataclass(frozen=True)
class ExportScope:
    allow_full: bool
    participant_id: str


def export_scope(principal: Principal) -> ExportScope:
    role = principal.role.value
    if role in {"GOV_AUTHORITY", "AUDITOR"}:
        return ExportScope(allow_full=True, participant_id=principal.participant_id)
    return ExportScope(allow_full=False, participant_id=principal.participant_id)
