from __future__ import annotations

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a request-id.
    - Accepts incoming X-Request-Id or generates one
    - Stores it in request.state.request_id
    - Returns it in response header
    """
    HEADER = "X-Request-Id"

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers[self.HEADER] = rid
        return response
