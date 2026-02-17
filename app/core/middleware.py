import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a request-id, placed into response headers.
    Uses configured header name (default X-Request-Id).
    """

    def __init__(self, app, header_name: str = "X-Request-Id"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = rid

        response = await call_next(request)
        response.headers[self.header_name] = rid
        return response