# app/core/clearland_phases.py
from enum import Enum


class ClearlandPhaseType(str, Enum):
    INIT = "INIT"
    DEVELOPER_ASK_OPEN = "DEVELOPER_ASK_OPEN"
    BUYER_BIDDING_OPEN = "BUYER_BIDDING_OPEN"
    PREFERENCES_COLLECTED = "PREFERENCES_COLLECTED"
    LOCKED = "LOCKED"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"