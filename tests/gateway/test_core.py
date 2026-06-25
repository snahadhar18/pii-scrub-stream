"""Tests for the core detector contract, redaction, registry and service."""

from __future__ import annotations

import pytest

from redactai.gateway.core.detector import (
    CallableDetector,
    DetectionSpan,
    DetectorProtocol,
    NullDetector,
)
from redactai.gateway.core.exceptions import DetectorError
from redactai.gateway.core.models import Record
from redactai.gateway.core.redaction import RedactionStrategy, Redactor
from redactai.gateway.core.registry import DetectorRegistry


def test_detection_span_validation() -> None:
    with pytest.raises(ValueError):
        DetectionSpan(start=5, end=2, label="X", text="??")
    with pytest.raises(ValueError):
        DetectionSpan(start=0, end=1, label="X", text="a", confidence=2.0)
    span = DetectionSpan(0, 3, "X", "abc")
    assert span.length == 3


def test_null_detector_is_protocol() -> None:
    assert isinstance(NullDetector(), DetectorProtocol)
    assert NullDetector().detect("anything") == ()


def test_callable_detector_adapts_function() -> None:
    def fn(text: str):
        return [DetectionSpan(0, 1, "C", text[:1])] if text else []

    det = CallableDetector(fn, name="c", labels=("C",))
    assert isinstance(det, DetectorProtocol)
    assert det.detect("hi")[0].label == "C"


def test_redaction_strategies() -> None:
    text = "mail a@b.com now"
    spans = [DetectionSpan(5, 10, "EMAIL", "a@b.c", 0.9, "[EMAIL]")]
    assert Redactor(RedactionStrategy.TAG).redact(text, spans) == "mail [EMAIL]om now"
    assert Redactor(RedactionStrategy.MASK).redact(text, spans) == "mail *****om now"
    assert Redactor(RedactionStrategy.REMOVE).redact(text, spans) == "mail om now"
    hashed = Redactor(RedactionStrategy.HASH).redact(text, spans)
    assert hashed.startswith("mail [EMAIL:") and hashed.endswith("om now")


def test_redaction_resolves_overlaps_by_confidence() -> None:
    text = "abcdef"
    spans = [
        DetectionSpan(0, 4, "LOW", "abcd", 0.5),
        DetectionSpan(2, 6, "HIGH", "cdef", 0.9),
    ]
    out = Redactor(RedactionStrategy.MASK).redact(text, spans)
    # The higher-confidence span wins; the overlapping lower one is dropped.
    assert out == "ab****"


def test_registry_register_and_create() -> None:
    reg = DetectorRegistry()
    reg.register("null", NullDetector)
    assert "null" in reg
    assert reg.names() == ["null"]
    assert isinstance(reg.create("null"), NullDetector)
    with pytest.raises(DetectorError):
        reg.create("missing")
    with pytest.raises(DetectorError):
        reg.register("null", NullDetector)  # duplicate
    reg.register("null", NullDetector, replace=True)  # ok


def test_scan_service_detects_and_redacts(scan_service) -> None:
    record = Record(id="1", content="ping a@b.com here")
    result = scan_service.scan(record, redact=True)
    assert result.hit_count == 1
    assert result.labels == ("EMAIL",)
    assert "[EMAIL]" in (result.redacted or "")


def test_scan_service_fail_open_skips_broken_detector(boom_detector, email_detector):
    from redactai.gateway.core.service import ScanService

    svc = ScanService([boom_detector, email_detector], fail_open=True)
    result = svc.scan(Record(id="1", content="a@b.com"))
    assert result.hit_count == 1  # email still found despite boom detector


def test_scan_service_fail_closed_raises(boom_detector):
    from redactai.gateway.core.service import ScanService

    svc = ScanService([boom_detector], fail_open=False)
    with pytest.raises(DetectorError):
        svc.scan(Record(id="1", content="x"))
