"""Structured logging configuration.

JSON in prod (one event per line, machine-parseable); pretty in dev.
Always log via `structlog.get_logger(__name__)` — never the stdlib `logging`
module directly, so contextvars (request_id, user_id) bind correctly.
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import Processor

from seedbank.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Wire structlog + stdlib logging once at process start."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
    ]

    if settings.env == "dev":
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Tame noisy libraries.
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(
            logging.WARNING if settings.env != "dev" else logging.INFO
        )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger. Prefer this over `logging.getLogger`."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
