from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Bucket:
    tokens: float
    last_ts: float


class InMemoryRateLimiter:
    """
    Token bucket:
      capacity tokens; refill rate tokens/sec.

    Keyed by (participant_id, route_key).
    """
    def __init__(self, capacity: int, refill_per_sec: float):
        self.capacity = float(capacity)
        self.refill_per_sec = float(refill_per_sec)
        self._buckets: Dict[Tuple[str, str], Bucket] = {}

    def allow(self, participant_id: str, route_key: str, cost: float = 1.0) -> bool:
        now = time.time()
        k = (participant_id, route_key)
        b = self._buckets.get(k)
        if b is None:
            b = Bucket(tokens=self.capacity, last_ts=now)
            self._buckets[k] = b

        # refill
        elapsed = max(0.0, now - b.last_ts)
        b.tokens = min(self.capacity, b.tokens + elapsed * self.refill_per_sec)
        b.last_ts = now

        if b.tokens >= cost:
            b.tokens -= cost
            return True
        return False


# Default limiter for bid submissions:
# 10 submissions per minute per endpoint per participant (capacity=10, refill=10/60)
BID_POST_LIMITER = InMemoryRateLimiter(capacity=10, refill_per_sec=10.0 / 60.0)