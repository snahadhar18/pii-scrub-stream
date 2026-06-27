"""Tests for configuration loading and the DI container."""

from __future__ import annotations

import pytest

from redactai.gateway.config.settings import Settings
from redactai.gateway.core.container import Container
from redactai.gateway.core.detector import NullDetector
from redactai.gateway.core.registry import DetectorRegistry


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDACTAI_PROCESSING__WORKERS", "16")
    monkeypatch.setenv("REDACTAI_API__PORT", "9100")
    settings = Settings()
    assert settings.processing.workers == 16
    assert settings.api.port == 9100


def test_container_falls_back_to_null_detector() -> None:
    settings = Settings(load_entry_point_detectors=False)
    container = Container(settings, registry=DetectorRegistry())
    assert len(container.detectors) == 1
    assert isinstance(container.detectors[0], NullDetector)


def test_container_resolves_registered_detectors() -> None:
    reg = DetectorRegistry()
    reg.register("null", NullDetector)
    settings = Settings(load_entry_point_detectors=False, detectors=("null",))
    container = Container(settings, registry=reg)
    assert [type(d) for d in container.detectors] == [NullDetector]
    # The scan service is memoized.
    assert container.scan_service is container.scan_service


def test_container_builds_engine() -> None:
    reg = DetectorRegistry()
    reg.register("null", NullDetector)
    settings = Settings(load_entry_point_detectors=False)
    container = Container(settings, registry=reg)
    engine = container.build_engine()
    assert engine.workers == settings.processing.workers
