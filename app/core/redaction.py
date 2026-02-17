from __future__ import annotations
import uuid

def mask_uuid(u: uuid.UUID | None) -> str | None:
    if not u:
        return None
    s = str(u)
    return s[:8] + "-REDACTED-" + s[-4:]