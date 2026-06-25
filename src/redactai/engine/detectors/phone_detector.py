"""Phone number detector (North-American and common international forms)."""

from __future__ import annotations

import re

from redactai.engine.detectors.base import RegexDetector

# Matches forms such as:
#   +1 (555) 123-4567 / 555-123-4567 / 555.123.4567 / +44 20 7946 0958
_PHONE_RE = re.compile(
    r"""
    (?<![\w.])                 # not part of a longer token/number
    (?:\+?\d{1,3}[\s.\-]?)?     # optional country code
    (?:\(?\d{2,4}\)?[\s.\-]?)   # area code, optionally parenthesised
    \d{3}[\s.\-]?\d{3,4}        # local number
    (?![\w])
    """,
    re.VERBOSE,
)


class PhoneDetector(RegexDetector):
    """Detect telephone numbers in a variety of common formats."""

    label = "PHONE"
    pattern = _PHONE_RE
    default_confidence = 0.85
    default_severity = "MEDIUM"

    def validate(self, value: str) -> bool:
        # Require at least 7 digits to avoid matching short numeric tokens.
        digits = sum(ch.isdigit() for ch in value)
        return 7 <= digits <= 15

    def get_confidence(self, value: str) -> float:
        """Phone numbers with country codes or parenthesised area codes are
        higher confidence since they follow a more specific format."""
        if value.strip().startswith("+"):
            return 0.95
        if "(" in value and ")" in value:
            return 0.92
        return self.default_confidence
