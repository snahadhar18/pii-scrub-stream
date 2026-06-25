"""Plain text / log file ingestion.

:class:`FileSource` streams a ``.txt`` or ``.log`` file one line at a time. Each
line becomes a :class:`Record`; the line number is recorded as the offset for
audit trails. Reading goes through Python's buffered text iterator, so memory
use stays flat regardless of file size.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import IO

from redactai.gateway.config.settings import IngestionSettings
from redactai.gateway.core.exceptions import IngestionError
from redactai.gateway.core.models import Record
from redactai.gateway.ingestion.base import BaseIngestionSource


class FileSource(BaseIngestionSource):
    """Yields one :class:`Record` per line of a text/log file."""

    def __init__(
        self,
        path: str | Path,
        *,
        settings: IngestionSettings | None = None,
        strip_newlines: bool = True,
        skip_blank: bool = False,
    ) -> None:
        self.path = Path(path)
        self.settings = settings or IngestionSettings()
        self.strip_newlines = strip_newlines
        self.skip_blank = skip_blank
        self.source_name = str(self.path)
        self._fh: IO[str] | None = None

    def open(self) -> None:
        if not self.path.exists():
            raise IngestionError(f"file not found: {self.path}")
        try:
            self._fh = self.path.open(
                "r", encoding=self.settings.encoding, errors="replace", newline=""
            )
        except OSError as exc:  # pragma: no cover - platform dependent
            raise IngestionError(f"cannot open {self.path}: {exc}") from exc

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def read_records(self) -> Iterator[Record]:
        owns = self._fh is None
        if owns:
            self.open()
        assert self._fh is not None
        try:
            for line_no, raw in enumerate(self._fh, start=1):
                content = raw.rstrip("\r\n") if self.strip_newlines else raw
                if self.skip_blank and not content.strip():
                    continue
                yield Record(
                    id=f"{self.source_name}:{line_no}",
                    content=content,
                    source=self.source_name,
                    offset=line_no,
                    metadata={"line": line_no},
                )
        finally:
            if owns:
                self.close()


__all__ = ["FileSource"]
