#app/policies/preference_policies.py
from __future__ import annotations
from app.policies.rbac import Principal


def enforce_slum_workflow_only(workflow: str) -> None:
    if workflow != "slum":
        raise PermissionError("Preferences submission is allowed only for slum workflow.")


def enforce_slum_dweller_role(principal: Principal) -> None:
    if principal.role.value != "SLUM_DWELLER":
        raise PermissionError("Only slum dwellers may submit preferences.")