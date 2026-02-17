from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limit import BID_POST_LIMITER


class BidRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Applies ONLY to POST bid endpoints.
    Requires auth middleware to set request.state.principal.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()

        # Only rate limit the POST bid endpoints
        if method == "POST" and path in {
            "/v1/bids/quote",
            "/v1/bids/ask",
            "/v1/bids/preferences",
        }:
            principal = getattr(request.state, "principal", None)
            if principal:
                route_key = f"{method}:{path}"
                ok = BID_POST_LIMITER.allow(principal.participant_id, route_key)
                if not ok:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded for bid submission."},
                        headers={"Retry-After": "60"},
                    )
        return await call_next(request)
