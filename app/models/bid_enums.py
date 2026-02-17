#app/models/bid_enums.py
from __future__ import annotations
from enum import Enum


class BidState(str, Enum):
    draft = "draft"
    submitted = "submitted"
    locked = "locked"