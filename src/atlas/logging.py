"""Structured logging. Every agent step, model call, and tool call is logged for auditability."""

from __future__ import annotations

import logging
import sys

import structlog

from atlas.config import get_settings


def setup_logging() -> None:
    """Configure structlog + stdlib logging. Call once at process start."""
    level = getattr(logging, get_settings().ATLAS_LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
