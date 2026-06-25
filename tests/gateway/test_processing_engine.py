"""Tests for the concurrent processing engine and streaming."""

from __future__ import annotations

import io

from redactai.gateway.core.models import Record
from redactai.gateway.core.service import ScanService
from redactai.gateway.observability.metrics import MetricsRegistry
from redactai.gateway.streaming.processor import ProcessingEngine
from redactai.gateway.streaming.stream import StreamProcessor


def _records(n: int) -> list[Record]:
    return [Record(id=str(i), content=f"mail a{i}@b.com line") for i in range(n)]


def test_engine_processes_all_in_order(scan_service: ScanService) -> None:
    with ProcessingEngine(scan_service, workers=4, batch_size=8) as engine:
        results = list(engine.process(_records(100)))
    assert len(results) == 100
    assert [r.record_id for r in results] == [str(i) for i in range(100)]
    assert all(r.hit_count == 1 for r in results)


def test_engine_run_returns_summary(scan_service: ScanService) -> None:
    metrics = MetricsRegistry()
    with ProcessingEngine(scan_service, workers=2, batch_size=4, metrics=metrics) as engine:
        results, summary = engine.run(_records(20))
    assert summary.records == 20
    assert summary.spans == 20
    assert summary.errors == 0
    assert summary.throughput_rps >= 0


def test_engine_fault_tolerance(boom_detector) -> None:
    metrics = MetricsRegistry()
    svc = ScanService([boom_detector], fail_open=False)
    with ProcessingEngine(svc, workers=2, batch_size=2, max_retries=1, metrics=metrics) as engine:
        results, summary = engine.run(_records(5))
    # All fail open at the engine level -> empty results, errors counted.
    assert len(results) == 5
    assert summary.errors == 5
    assert metrics.counter("rg_records_retried") > 0


def test_engine_requires_start(scan_service: ScanService) -> None:
    engine = ProcessingEngine(scan_service)
    try:
        list(engine.process(_records(1)))
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_stream_processor_filters_stdin(scan_service: ScanService) -> None:
    engine = ProcessingEngine(scan_service, workers=2, batch_size=4, redact=True)
    stdin = io.StringIO("contact a@b.com\nplain line\n")
    stdout = io.StringIO()
    processor = StreamProcessor(engine, install_signal_handlers=False, emit_redacted=True)
    count = processor.run(stdin, stdout)
    assert count == 2
    out = stdout.getvalue().splitlines()
    assert out[0] == "contact [EMAIL]"
    assert out[1] == "plain line"
