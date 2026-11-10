"""
backend/app/core/logging.py
Structured logging configuration using structlog.
"""
import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """
    Configure structlog for the application.
    JSON in production, coloured console in development.
    """
    settings = get_settings()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENVIRONMENT == "production":
        # JSON output for log aggregation (Cloud Logging, Loki, etc.)
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Suppress noisy uvicorn access logs in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module."""
    return structlog.get_logger(name)

