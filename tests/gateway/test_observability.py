"""Tests for metrics, audit logging and health checks."""

from __future__ import annotations

import json
from pathlib import Path

from redactai.gateway.observability.audit import AuditEvent, AuditLogger
from redactai.gateway.observability.health import HealthCheck, HealthStatus
from redactai.gateway.observability.metrics import MetricsRegistry, Timer


def test_metrics_counters_gauges_histograms() -> None:
    m = MetricsRegistry()
    m.increment("requests", 2)
    m.increment("requests")
    m.set_gauge("queue_depth", 7)
    m.observe("latency_ms", 12.5)
    assert m.counter("requests") == 3
    assert m.gauge("queue_depth") == 7
    snap = m.snapshot()
    assert snap["counters"]["requests"] == 3
    assert snap["histograms"]["latency_ms"]["count"] == 1


def test_metrics_prometheus_render() -> None:
    m = MetricsRegistry()
    m.increment("rg_records_processed", 5)
    text = m.render_prometheus()
    assert "rg_records_processed 5" in text
    assert "# TYPE rg_records_processed counter" in text


def test_timer_records_observation() -> None:
    m = MetricsRegistry()
    with Timer(m, "op_ms"):
        pass
    assert m.snapshot()["histograms"]["op_ms"]["count"] == 1


def test_audit_logger_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    logger = AuditLogger(str(path))
    logger.emit(AuditEvent(action="scan", record_id="1", source="api", hit_count=2))
    logger.close()
    line = path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["action"] == "scan"
    assert payload["hit_count"] == 2


def test_health_check_aggregation() -> None:
    hc = HealthCheck(version="1.2.3")
    hc.add("ok", lambda: True)
    assert hc.run().status is HealthStatus.HEALTHY
    hc.add("bad", lambda: False)
    assert hc.run().status is HealthStatus.DEGRADED
    hc2 = HealthCheck()
    hc2.add("explodes", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert hc2.run().status is HealthStatus.UNHEALTHY
