"""Tests for the FastAPI service.

Skipped automatically when FastAPI/httpx are not installed so the core suite
still runs in a minimal environment.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from redactai.gateway.config.settings import Settings  # noqa: E402
from redactai.gateway.core.container import Container  # noqa: E402
from redactai.gateway.core.detector import DetectionSpan, Detector  # noqa: E402
from redactai.gateway.core.registry import DetectorRegistry  # noqa: E402


class FakeEmailDetector(Detector):
    """Test fixture: flags ``word@word.word`` substrings as EMAIL spans."""

    name = "fake_email"
    labels = ("EMAIL",)
    _pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        return [
            DetectionSpan(m.start(), m.end(), "EMAIL", m.group(), 0.99, "[EMAIL]")
            for m in self._pattern.finditer(text)
        ]


@pytest.fixture
def client() -> TestClient:
    from redactai.gateway.api.app import create_app

    reg = DetectorRegistry()
    reg.register("fake_email", FakeEmailDetector)
    settings = Settings(load_entry_point_detectors=False, detectors=("fake_email",))
    app = create_app(settings=settings, container=Container(settings, registry=reg))
    with TestClient(app) as c:
        yield c


def test_scan_endpoint(client: TestClient) -> None:
    resp = client.post("/scan", json={"text": "mail a@b.com", "redact": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hit_count"] == 1
    assert body["labels"] == ["EMAIL"]
    assert "[EMAIL]" in body["redacted"]


def test_stream_endpoint(client: TestClient) -> None:
    resp = client.post("/stream", json={"lines": ["a@b.com", "nothing"], "redact": True})
    assert resp.status_code == 200
    rows = [json.loads(line) for line in resp.text.splitlines() if line]
    assert len(rows) == 2
    assert rows[0]["hit_count"] == 1
    assert rows[1]["hit_count"] == 0


def test_ingest_endpoint(client: TestClient) -> None:
    content = b"a@b.com\nplain\nc@d.com\n"
    resp = client.post(
        "/ingest",
        files={"file": ("data.log", content, "text/plain")},
        params={"redact": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["records"] == 3
    assert body["spans"] == 2


def test_health_and_metrics(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] in {"healthy", "degraded", "unhealthy"}

    metrics = client.get("/metrics", params={"fmt": "json"})
    assert metrics.status_code == 200
    assert "counters" in metrics.json()


def test_validation_error(client: TestClient) -> None:
    resp = client.post("/scan", json={})  # missing required 'text'
    assert resp.status_code == 422
