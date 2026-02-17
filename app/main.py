from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.api.v1.router import v1_router
from app.core.middleware_rate_limit import BidRateLimitMiddleware

from fastapi import FastAPI
import logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Middleware: Request ID
    app.add_middleware(RequestIdMiddleware, header_name=settings.request_id_header)

    # API v1
    app.include_router(v1_router, prefix=settings.api_prefix)

    return app


app = create_app()


#middleware conflict check and fix