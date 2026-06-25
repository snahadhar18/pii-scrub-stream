"""CSV ingestion.

:class:`CSVSource` streams a CSV file row by row using the stdlib ``csv``
reader, which parses incrementally and never materializes the whole file. Each
row becomes a :class:`Record` whose ``content`` is the row rendered as text and
whose ``metadata`` preserves the structured column->value mapping so downstream
audit logs can point at the exact field that triggered a detection.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import IO

from redactai.gateway.config.settings import IngestionSettings
from redactai.gateway.core.exceptions import IngestionError
from redactai.gateway.core.models import Record
from redactai.gateway.ingestion.base import BaseIngestionSource


class CSVSource(BaseIngestionSource):
    """Yields one :class:`Record` per CSV row.

    Args:
        path: CSV file path.
        has_header: Treat the first row as a header for column names.
        columns: Restrict scanning to these columns (by name or index). When
            ``None`` every column is included in the rendered content.
        content_separator: String used to join field values into ``content``.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        settings: IngestionSettings | None = None,
        has_header: bool = True,
        columns: Sequence[str] | None = None,
        content_separator: str = " ",
    ) -> None:
        self.path = Path(path)
        self.settings = settings or IngestionSettings()
        self.has_header = has_header
        self.columns = list(columns) if columns is not None else None
        self.content_separator = content_separator
        self.source_name = str(self.path)
        self._fh: IO[str] | None = None

    def open(self) -> None:
        if not self.path.exists():
            raise IngestionError(f"file not found: {self.path}")
        self._fh = self.path.open(
            "r", encoding=self.settings.encoding, errors="replace", newline=""
        )

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
            reader = csv.reader(self._fh, delimiter=self.settings.csv_delimiter)
            header: list[str] | None = None
            start = 1
            if self.has_header:
                try:
                    header = next(reader)
                except StopIteration:
                    return
                start = 2
            for row_no, row in enumerate(reader, start=start):
                fields = self._row_mapping(header, row)
                content = self._render(header, row)
                yield Record(
                    id=f"{self.source_name}:{row_no}",
                    content=content,
                    source=self.source_name,
                    offset=row_no,
                    metadata={"row": row_no, "fields": fields},
                )
        except csv.Error as exc:
            raise IngestionError(f"CSV parse error in {self.path}: {exc}") from exc
        finally:
            if owns:
                self.close()

    def _row_mapping(self, header: list[str] | None, row: Sequence[str]) -> dict[str, str]:
        if header is not None:
            return {header[i]: v for i, v in enumerate(row) if i < len(header)}
        return {str(i): v for i, v in enumerate(row)}

    def _render(self, header: list[str] | None, row: Sequence[str]) -> str:
        if self.columns is None:
            return self.content_separator.join(row)
        selected: list[str] = []
        for col in self.columns:
            if header is not None and col in header:
                idx = header.index(col)
            elif col.isdigit():
                idx = int(col)
            else:
                continue
            if idx < len(row):
                selected.append(row[idx])
        return self.content_separator.join(selected)


__all__ = ["CSVSource"]
