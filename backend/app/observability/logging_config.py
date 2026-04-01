"""
Structured JSON logging configuration (RC-125).

Call configure_logging() once at application startup (from main.py).
All subsequent getLogger() calls inherit the JSON formatter on the root handler.

Works whether modules load before or after the FastAPI app starts because
configure_logging() is idempotent and touches only the root logger.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with a JSON formatter.

    Safe to call multiple times — subsequent calls are no-ops.
    Never raises; falls back to basicConfig on any error so the app
    always gets some logging.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    try:
        from pythonjsonlogger.jsonlogger import JsonFormatter

        fmt = JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(level)
        # Remove any pre-existing handlers installed by uvicorn or pytest
        root.handlers.clear()
        root.addHandler(handler)
    except Exception:
        logging.basicConfig(stream=sys.stdout, level=level)
    _CONFIGURED = True
