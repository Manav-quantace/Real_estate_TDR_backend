from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_dumps(obj: Dict[str, Any]) -> str:
    # Deterministic JSON string: sorted keys, no whitespace
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hash_chain(prev_hash: str, payload: Dict[str, Any]) -> str:
    return sha256_hex(prev_hash + canonical_dumps(payload))