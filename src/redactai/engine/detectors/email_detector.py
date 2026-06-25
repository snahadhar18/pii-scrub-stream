"""Email address detector."""

from __future__ import annotations

import re

from redactai.engine.detectors.base import RegexDetector

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)


class EmailDetector(RegexDetector):
    """Detect RFC-5322-ish email addresses (pragmatic, not fully spec-compliant)."""

    label = "EMAIL"
    pattern = _EMAIL_RE
    default_confidence = 0.99
    default_severity = "MEDIUM"
