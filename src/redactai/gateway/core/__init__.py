"""Core domain layer: detector contract, models, services and wiring.

The core layer is deliberately free of I/O concerns (no file handles, no HTTP,
no thread pools). It defines *what* the system does -- detect spans in text and
produce redacted output -- while the surrounding layers (``ingestion``,
``streaming``, ``api``) decide *how* data flows in and out.
"""

from __future__ import annotations

from redactai.gateway.core.container import Container
from redactai.gateway.core.detector import (
    DetectionSpan,
    Detector,
    DetectorProtocol,
    NullDetector,
)
from redactai.gateway.core.exceptions import (
    ConfigurationError,
    DetectorError,
    IngestionError,
    ProcessingError,
    RagGuardianError,
)
from redactai.gateway.core.models import Record, ScanResult, SpanModel
from redactai.gateway.core.redaction import RedactionStrategy, Redactor
from redactai.gateway.core.registry import DetectorRegistry, global_registry
from redactai.gateway.core.service import ScanService

__all__ = [
    "Container",
    "Detector",
    "DetectorProtocol",
    "DetectionSpan",
    "NullDetector",
    "RagGuardianError",
    "ConfigurationError",
    "IngestionError",
    "ProcessingError",
    "DetectorError",
    "Record",
    "ScanResult",
    "SpanModel",
    "Redactor",
    "RedactionStrategy",
    "DetectorRegistry",
    "global_registry",
    "ScanService",
]
