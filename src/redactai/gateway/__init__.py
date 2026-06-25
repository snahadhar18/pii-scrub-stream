"""RedactAI -- enterprise-grade AI security gateway infrastructure.

This package owns the *infrastructure* around PII/secret detection: ingestion,
stream processing, concurrency, the HTTP API, observability, configuration and
deployment. It does **not** implement detection logic. Detectors are external
plugins integrated through the :class:`redactai.gateway.core.detector.Detector`
contract and the :class:`redactai.gateway.core.registry.DetectorRegistry`.

The public surface intentionally re-exports only the stable, high-level
building blocks so downstream code can depend on a small, well-defined API.
"""

from __future__ import annotations

__version__ = "0.1.0"

from redactai.gateway.core.detector import (
    DetectionSpan,
    Detector,
    DetectorProtocol,
    NullDetector,
)
from redactai.gateway.core.models import Record, ScanResult, SpanModel

__all__ = [
    "__version__",
    "Detector",
    "DetectorProtocol",
    "DetectionSpan",
    "NullDetector",
    "Record",
    "ScanResult",
    "SpanModel",
]
