"""
AdaptixC2 MCP — Structured Logging Utility
Uses structlog for human-readable + JSON structured logs.
"""

import logging
import sys
import structlog
from config import Config


def setup_logging() -> None:
    """Configure structlog with a clean, readable format."""

    level = getattr(logging, Config.MCP_LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def get_logger(name: str = "AdaptixC2-MCP-Server") -> structlog.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
