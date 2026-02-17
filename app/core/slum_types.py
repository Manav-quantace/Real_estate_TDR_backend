#app/core/slum_types.py
from __future__ import annotations
from enum import Enum


class SlumPortalType(str, Enum):
    SLUM_DWELLER = "SLUM_DWELLER"
    SLUM_LAND_DEVELOPER = "DEVELOPER"
    AFFORDABLE_HOUSING_DEV = "AFFORDABLE_HOUSING_DEV"
