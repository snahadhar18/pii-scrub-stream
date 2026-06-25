"""Credit-card number detector with Luhn validation."""

from __future__ import annotations

import re

from pii_scrub_stream.detectors.base import RegexDetector

# 13-19 digits, optionally grouped with single spaces or hyphens.
# Anchored on a digit at both ends so a trailing separator is never consumed.
_CC_RE = re.compile(r"\b\d(?:[ \-]?\d){12,18}\b")


def luhn_checksum_valid(number: str) -> bool:
    """Return ``True`` if ``number`` (digits only) passes the Luhn check."""
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    # Double every second digit from the right.
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class CreditCardDetector(RegexDetector):
    """Detect credit-card-like numbers validated by the Luhn algorithm."""

    label = "CREDIT_CARD"
    pattern = _CC_RE

    def validate(self, value: str) -> bool:
        digits = [ch for ch in value if ch.isdigit()]
        if not 13 <= len(digits) <= 19:
            return False
        return luhn_checksum_valid(value)
