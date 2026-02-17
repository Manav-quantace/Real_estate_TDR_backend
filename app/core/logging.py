import logging
import sys
from pythonjsonlogger import jsonlogger
from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Minimal structured logging (JSON) for backend skeleton.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # clear handlers if reloaded
    root.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "name": "logger"},
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
