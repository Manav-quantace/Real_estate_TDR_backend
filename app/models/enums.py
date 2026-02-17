#app/models/enums.py
from __future__ import annotations
from enum import Enum


class ParticipantRole(str, Enum):
    BUYER = "BUYER"
    DEVELOPER = "DEVELOPER"
    OWNER_SOCIETY = "OWNER_SOCIETY"
    SLUM_DWELLER = "SLUM_DWELLER"
    AFFORDABLE_HOUSING_DEV = "AFFORDABLE_HOUSING_DEV"
    GOV_AUTHORITY = "GOV_AUTHORITY"
    AUDITOR = "AUDITOR"


class RoundState(str, Enum):
    # structural lifecycle
    draft = "draft"
    submitted = "submitted"
    locked = "locked"


class ChargeType(str, Enum):
    GC = "GC"
    GCU = "GCU"
