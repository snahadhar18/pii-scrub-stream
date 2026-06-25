"""Service layer -- orchestrates detectors and redaction over a record.

:class:`ScanService` is the single place that knows how to turn a
:class:`Record` into a :class:`ScanResult`: run every configured detector,
merge their spans, optionally redact, and time the work. It depends only on the
detector *protocol* and a :class:`Redactor`, so it is trivially unit-testable
and free of any I/O or detection logic.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence

from redactai.gateway.core.detector import DetectionSpan, DetectorProtocol
from redactai.gateway.core.exceptions import DetectorError
from redactai.gateway.core.models import Record, ScanResult, SpanModel
from redactai.gateway.core.redaction import Redactor

logger = logging.getLogger(__name__)


class ScanService:
    """Coordinates detection + redaction for individual records.

    Args:
        detectors: The detector plugins to run. Order is preserved but spans are
            sorted deterministically in the result.
        redactor: Strategy object used when ``redact=True``.
        fail_open: When ``True`` (default) a detector raising an exception is
            logged and skipped rather than failing the whole record -- a security
            gateway should degrade gracefully, not drop traffic. Set ``False`` in
            strict environments where any detector failure must surface.
    """

    def __init__(
        self,
        detectors: Sequence[DetectorProtocol],
        redactor: Redactor | None = None,
        *,
        fail_open: bool = True,
    ) -> None:
        self._detectors = list(detectors)
        self._redactor = redactor or Redactor()
        self._fail_open = fail_open

    @property
    def detectors(self) -> list[DetectorProtocol]:
        """The detectors this service runs."""
        return list(self._detectors)

    def detect(self, text: str) -> list[DetectionSpan]:
        """Run all detectors over ``text`` and return merged spans."""
        spans: list[DetectionSpan] = []
        for detector in self._detectors:
            try:
                spans.extend(detector.detect(text))
            except Exception as exc:  # noqa: BLE001
                if not self._fail_open:
                    raise DetectorError(f"detector {detector!r} failed") from exc
                logger.exception("detector %r raised; skipping (fail-open)", detector)
        spans.sort(key=lambda s: (s.start, s.end))
        return spans

    def scan(self, record: Record, *, redact: bool = False) -> ScanResult:
        """Scan a single record and return a structured result."""
        start = time.perf_counter()
        spans = self.detect(record.content)
        redacted = self._redactor.redact(record.content, spans) if redact else None
        duration_ms = (time.perf_counter() - start) * 1000.0
        return ScanResult(
            record_id=record.id,
            source=record.source,
            spans=tuple(SpanModel.from_span(s) for s in spans),
            redacted=redacted,
            duration_ms=duration_ms,
        )


__all__ = ["ScanService"]
