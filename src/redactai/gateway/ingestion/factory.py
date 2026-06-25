"""Source factory -- pick the right ingestion source for an input.

Centralizing source selection keeps the CLI and API free of file-type branching
and gives one obvious place to register new source types.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from redactai.gateway.config.settings import IngestionSettings
from redactai.gateway.core.exceptions import IngestionError
from redactai.gateway.ingestion.base import BaseIngestionSource
from redactai.gateway.ingestion.csv_source import CSVSource
from redactai.gateway.ingestion.file_source import FileSource
from redactai.gateway.ingestion.json_source import JSONSource


class SourceType(str, Enum):
    """Supported ingestion source types."""

    TEXT = "text"
    CSV = "csv"
    JSON = "json"

    @classmethod
    def from_suffix(cls, path: Path) -> SourceType:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return cls.CSV
        if suffix in {".json", ".jsonl", ".ndjson"}:
            return cls.JSON
        return cls.TEXT  # .txt, .log, and everything else


class SourceFactory:
    """Builds :class:`BaseIngestionSource` instances from paths or explicit types."""

    def __init__(self, settings: IngestionSettings | None = None) -> None:
        self.settings = settings or IngestionSettings()

    def for_path(
        self, path: str | Path, source_type: SourceType | None = None, **kwargs: object
    ) -> BaseIngestionSource:
        """Return an opened-capable source appropriate for ``path``.

        Args:
            path: Input file path.
            source_type: Force a specific type; inferred from the suffix when
                omitted.
            **kwargs: Forwarded to the concrete source constructor.
        """
        p = Path(path)
        st = source_type or SourceType.from_suffix(p)
        if st is SourceType.CSV:
            return CSVSource(p, settings=self.settings, **kwargs)  # type: ignore[arg-type]
        if st is SourceType.JSON:
            return JSONSource(p, settings=self.settings, **kwargs)  # type: ignore[arg-type]
        if st is SourceType.TEXT:
            return FileSource(p, settings=self.settings, **kwargs)  # type: ignore[arg-type]
        raise IngestionError(f"unsupported source type: {st}")  # pragma: no cover


__all__ = ["SourceFactory", "SourceType"]
