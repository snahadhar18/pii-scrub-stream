"""Request/response models for the HTTP API.

Keeping these separate from the core domain models lets the wire contract evolve
independently and gives FastAPI explicit schemas for OpenAPI generation and
request/response validation.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field

from redactai.gateway.core.models import ScanResult, SpanModel


class ScanRequest(BaseModel):
    """Scan a single piece of text."""

    text: str = Field(..., description="Text to scan for sensitive data.", max_length=10_000_000)
    redact: bool = Field(default=True, description="Return redacted text alongside spans.")


class ScanResponse(BaseModel):
    """Result of scanning one text payload."""

    record_id: str
    spans: tuple[SpanModel, ...] = ()
    redacted: str | None = None
    duration_ms: float = 0.0
    hit_count: int = 0
    labels: tuple[str, ...] = ()

    @classmethod
    def from_result(cls, result: ScanResult) -> ScanResponse:
        return cls(
            record_id=result.record_id,
            spans=result.spans,
            redacted=result.redacted,
            duration_ms=result.duration_ms,
            hit_count=result.hit_count,
            labels=result.labels,
        )


class StreamRequest(BaseModel):
    """Scan many lines; the response is streamed back as JSON lines."""

    lines: list[str] = Field(..., description="Lines/records to scan.", min_length=1)
    redact: bool = Field(default=True)


class IngestResponse(BaseModel):
    """Summary returned after ingesting and scanning an uploaded file."""

    source: str
    records: int
    spans: int
    duration_ms: float
    errors: int
    label_counts: Mapping[str, int] = {}


class HealthResponse(BaseModel):
    """Health probe response."""

    status: str
    version: str
    checks: Mapping[str, bool] = {}


class ErrorResponse(BaseModel):
    """Uniform error envelope for non-2xx responses."""

    error: str
    detail: str
    type: str


__all__ = [
    "ScanRequest",
    "ScanResponse",
    "StreamRequest",
    "IngestResponse",
    "HealthResponse",
    "ErrorResponse",
]
