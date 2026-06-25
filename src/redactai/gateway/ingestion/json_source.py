"""JSON / JSON-Lines ingestion.

Two layouts are supported with memory efficiency in mind:

* **JSON Lines** (``.jsonl``/``.ndjson``): one JSON value per line. Streamed
  line by line, so files of any size use constant memory.
* **JSON array** (``.json``): a top-level ``[...]`` of objects. When the
  optional ``ijson`` package is installed it is parsed incrementally; otherwise
  we fall back to ``json.load`` (documented tradeoff: the array must then fit in
  memory).

Each top-level value becomes a :class:`Record`. A ``content_field`` may be
named to scan a single field; otherwise the whole value is serialized to text.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

from redactai.gateway.config.settings import IngestionSettings
from redactai.gateway.core.exceptions import IngestionError
from redactai.gateway.core.models import Record
from redactai.gateway.ingestion.base import BaseIngestionSource

_JSONL_SUFFIXES = {".jsonl", ".ndjson"}


class JSONSource(BaseIngestionSource):
    """Yields one :class:`Record` per top-level JSON value."""

    def __init__(
        self,
        path: str | Path,
        *,
        settings: IngestionSettings | None = None,
        json_lines: bool | None = None,
        content_field: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.settings = settings or IngestionSettings()
        if json_lines is None:
            json_lines = self.path.suffix.lower() in _JSONL_SUFFIXES
        self.json_lines = json_lines
        self.content_field = content_field
        self.source_name = str(self.path)
        self._fh: IO[str] | None = None

    def open(self) -> None:
        if not self.path.exists():
            raise IngestionError(f"file not found: {self.path}")
        self._fh = self.path.open("r", encoding=self.settings.encoding, errors="replace")

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
            if self.json_lines:
                yield from self._read_lines()
            else:
                yield from self._read_array()
        finally:
            if owns:
                self.close()

    def _read_lines(self) -> Iterator[Record]:
        assert self._fh is not None
        for line_no, raw in enumerate(self._fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestionError(
                    f"invalid JSON on line {line_no} of {self.path}: {exc}"
                ) from exc
            yield self._to_record(value, line_no)

    def _read_array(self) -> Iterator[Record]:
        assert self._fh is not None
        try:  # streaming path
            import ijson  # type: ignore

            for index, value in enumerate(ijson.items(self._fh, "item"), start=1):
                yield self._to_record(value, index)
            return
        except ImportError:
            pass
        # Fallback: load the whole array (must fit in memory).
        self._fh.seek(0)
        try:
            data = json.load(self._fh)
        except json.JSONDecodeError as exc:
            raise IngestionError(f"invalid JSON in {self.path}: {exc}") from exc
        if not isinstance(data, list):
            raise IngestionError(
                f"expected a top-level JSON array in {self.path}; got {type(data).__name__}"
            )
        for index, value in enumerate(data, start=1):
            yield self._to_record(value, index)

    def _to_record(self, value: Any, index: int) -> Record:
        if self.content_field is not None and isinstance(value, dict):
            content = str(value.get(self.content_field, ""))
        elif isinstance(value, str):
            content = value
        else:
            content = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return Record(
            id=f"{self.source_name}:{index}",
            content=content,
            source=self.source_name,
            offset=index,
            metadata={"index": index},
        )


__all__ = ["JSONSource"]
