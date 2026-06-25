"""Audit logging -- a tamper-evident-ish trail of security-relevant events.

Audit events are distinct from operational logs: they record *what was scanned*
and *what was found* (by label and count -- never the sensitive value itself) so
the gateway can prove coverage to auditors without leaking PII. Events are
emitted as JSON lines either to a file or stdout.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import IO


@dataclass(frozen=True)
class AuditEvent:
    """A single audit record. Never contains raw sensitive values."""

    action: str
    record_id: str
    source: str
    label_counts: Mapping[str, int] = field(default_factory=dict)
    hit_count: int = 0
    actor: str = "system"
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)


class AuditLogger:
    """Thread-safe JSON-lines audit sink (file or stdout)."""

    def __init__(self, path: str | None = None, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._path = Path(path) if path else None
        self._lock = threading.Lock()
        self._fh: IO[str] | None = None
        if self.enabled and self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self._path.open("a", encoding="utf-8")

    def emit(self, event: AuditEvent) -> None:
        """Write an audit event (no-op when disabled)."""
        if not self.enabled:
            return
        line = event.to_json()
        with self._lock:
            stream = self._fh or sys.stdout
            stream.write(line + "\n")
            stream.flush()

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None


__all__ = ["AuditEvent", "AuditLogger"]
