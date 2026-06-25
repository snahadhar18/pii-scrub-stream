"""Validated domain models shared across layers.

These Pydantic models are the *boundary* representations: they validate and
serialize data crossing the edges of the system (CLI args, API payloads,
ingestion records, scan results). The hot-path :class:`DetectionSpan` stays a
plain dataclass; :class:`SpanModel` is its serialization-friendly twin.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from redactai.gateway.core.detector import DetectionSpan


class Record(BaseModel):
    """A single unit of work flowing through the system.

    A record may be a log line, a CSV row rendered as text, or a JSON document.
    ``content`` is always the text that detectors will inspect; ``metadata``
    carries provenance (file name, row number, byte offset) for audit trails.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable identifier, unique within a batch/stream.")
    content: str = Field(..., description="Raw text to be scanned by detectors.")
    source: str = Field("inline", description="Logical origin, e.g. a file path or 'stdin'.")
    offset: int | None = Field(
        default=None, description="Line number or byte offset within the source."
    )
    metadata: Mapping[str, Any] = Field(
        default_factory=dict, description="Arbitrary provenance attached by the ingestion layer."
    )


class SpanModel(BaseModel):
    """Serializable representation of a :class:`DetectionSpan`."""

    model_config = ConfigDict(frozen=True)

    start: int
    end: int
    label: str
    text: str
    confidence: float = 1.0
    replacement: str | None = None

    @classmethod
    def from_span(cls, span: DetectionSpan) -> SpanModel:
        """Build a model from a runtime span."""
        return cls(
            start=span.start,
            end=span.end,
            label=span.label,
            text=span.text,
            confidence=span.confidence,
            replacement=span.replacement,
        )

    def to_span(self) -> DetectionSpan:
        """Convert back into the hot-path dataclass."""
        return DetectionSpan(
            start=self.start,
            end=self.end,
            label=self.label,
            text=self.text,
            confidence=self.confidence,
            replacement=self.replacement,
        )


class ScanResult(BaseModel):
    """Outcome of scanning a single :class:`Record`."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    source: str = "inline"
    spans: tuple[SpanModel, ...] = ()
    redacted: str | None = Field(
        default=None, description="Redacted content when redaction was requested."
    )
    duration_ms: float = Field(default=0.0, description="Wall-clock detection time (ms).")

    @property
    def hit_count(self) -> int:
        """Number of spans detected in the record."""
        return len(self.spans)

    @property
    def labels(self) -> tuple[str, ...]:
        """Distinct labels present in this result, in first-seen order."""
        seen: dict[str, None] = {}
        for span in self.spans:
            seen.setdefault(span.label, None)
        return tuple(seen)


class ScanSummary(BaseModel):
    """Aggregate statistics for a batch or stream run."""

    records: int = 0
    spans: int = 0
    bytes_processed: int = 0
    duration_ms: float = 0.0
    errors: int = 0
    label_counts: Mapping[str, int] = Field(default_factory=dict)

    @property
    def throughput_rps(self) -> float:
        """Records processed per second over the run."""
        seconds = self.duration_ms / 1000.0
        return self.records / seconds if seconds > 0 else 0.0


__all__ = ["Record", "SpanModel", "ScanResult", "ScanSummary"]
