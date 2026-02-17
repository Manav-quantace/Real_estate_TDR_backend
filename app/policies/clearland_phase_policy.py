# app/policies/clearland_phase_policy.py
from typing import Set
from app.core.clearland_phases import ClearlandPhaseType
from app.services.clearland_phase_service import ClearlandPhaseService

# phase → allowed actions (strings used across system)
PHASE_ACTIONS: dict[ClearlandPhaseType, Set[str]] = {
    ClearlandPhaseType.DEVELOPER_ASK_OPEN: {"SUBMIT_ASK"},
    ClearlandPhaseType.BUYER_BIDDING_OPEN: {"SUBMIT_QUOTE"},
    ClearlandPhaseType.PREFERENCES_COLLECTED: {"SUBMIT_PREFERENCES"},
}


def enforce_phase_allows_action(
    *,
    db,
    workflow: str,
    project_id,
    action: str,
):
    """
    Enforce Clearland phase guard for actions.

    No-op for non-clearland workflows.
    Raises PermissionError if phase not initialized or action not allowed.
    """
    if workflow != "clearland":
        return  # no-op for other workflows

    phase = ClearlandPhaseService().get_current_phase(db, project_id=project_id)
    if not phase:
        raise PermissionError("Clearland phase not initialized for project.")

    try:
        phase_enum = ClearlandPhaseType(phase.phase)
    except Exception:
        raise PermissionError(f"Unknown clearland phase: {phase.phase}")

    allowed = PHASE_ACTIONS.get(phase_enum, set())
    if action not in allowed:
        raise PermissionError(
            f"Action {action} not allowed in clearland phase {phase_enum.value}."
        )