from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_hash(payload: Dict[str, Any]) -> str:
    """
    SHA-256 of canonical JSON representation.
    Deterministic: sorted keys, no whitespace variance.
    """
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()