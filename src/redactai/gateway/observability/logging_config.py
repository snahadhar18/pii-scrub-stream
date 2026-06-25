"""Structured logging configuration.

Provides a JSON log formatter and a single ``configure_logging`` entry point so
every process (CLI, API, worker) emits consistent, machine-parseable logs.
Extra structured fields can be attached via ``logger.info(msg, extra={...})``
and will appear as top-level JSON keys.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

#: Standard ``LogRecord`` attributes we never want to duplicate as extras.
_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Configure the root logger once for the whole process.

    Args:
        level: Log level name (``"DEBUG"``, ``"INFO"`` ...).
        fmt: ``"json"`` for structured logs or ``"text"`` for human-readable.
    """
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (thin wrapper for a consistent import site)."""
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger", "JsonFormatter"]
