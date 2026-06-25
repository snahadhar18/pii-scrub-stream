"""Shared pytest fixtures for the RedactAI test suite.

Provides lightweight *test-only* detectors. These are fixtures, not production
detection logic: the package never ships detector implementations.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import pytest

from redactai.gateway.core.detector import DetectionSpan, Detector
from redactai.gateway.core.registry import DetectorRegistry
from redactai.gateway.core.service import ScanService


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


class BoomDetector(Detector):
    """Test fixture: always raises, to exercise fault tolerance."""

    name = "boom"

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        raise RuntimeError("boom")


@pytest.fixture
def email_detector() -> FakeEmailDetector:
    return FakeEmailDetector()


@pytest.fixture
def boom_detector() -> BoomDetector:
    return BoomDetector()


@pytest.fixture
def scan_service(email_detector: FakeEmailDetector) -> ScanService:
    return ScanService([email_detector])


@pytest.fixture
def registry(email_detector: FakeEmailDetector) -> DetectorRegistry:
    reg = DetectorRegistry()
    reg.register("fake_email", FakeEmailDetector)
    return reg
