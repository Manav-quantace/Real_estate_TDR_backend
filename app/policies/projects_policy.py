#/app/policies/projects_policy.py
from __future__ import annotations

from app.policies.rbac import Principal


def can_create_project(principal: Principal, workflow: str) -> bool:
    # Minimal strictness: creation is done by workflow-appropriate roles
    role = principal.role.value

    if workflow == "saleable":
        return role == "OWNER_SOCIETY"
    if workflow == "slum":
        return role in {"GOV_AUTHORITY"}  # govt owned land projects
    if workflow == "subsidized":
        return role in {"GOV_AUTHORITY"}
    if workflow == "clearland":
        return role in {"GOV_AUTHORITY"}  # clear land parcels registry
    return False


def can_update_project(principal: Principal, workflow: str) -> bool:
    role = principal.role.value
    if workflow == "saleable":
        return role == "OWNER_SOCIETY"
    if workflow in {"slum", "subsidized", "clearland"}:
        return role in {"GOV_AUTHORITY"}
    return False


def can_publish_project(principal: Principal, workflow: str) -> bool:
    # Publishing is a sensitive action; keep authority for non-saleable
    role = principal.role.value
    if workflow == "saleable":
        return role == "OWNER_SOCIETY"
    return role == "GOV_AUTHORITY"