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
    default_confidence = 0.95

    def validate(self, value: str) -> bool:
        digits = [ch for ch in value if ch.isdigit()]
        if not 13 <= len(digits) <= 19:
            return False
        return luhn_checksum_valid(value)

    def get_confidence(self, value: str) -> float:
        """Cards with standard prefixes (Visa, MC, Amex, Discover) get higher
        confidence. Luhn-valid but non-standard-prefix cards are slightly lower."""
        digits = "".join(ch for ch in value if ch.isdigit())
        # Visa: starts with 4
        if digits.startswith("4") and len(digits) in (13, 16, 19):
            return 0.99
        # Mastercard: starts with 51-55 or 2221-2720
        if digits[:2] in ("51", "52", "53", "54", "55"):
            return 0.99
        # Amex: starts with 34 or 37
        if digits[:2] in ("34", "37") and len(digits) == 15:
            return 0.99
        # Discover: starts with 6011 or 65
        if digits.startswith("6011") or digits.startswith("65"):
            return 0.98
        return self.default_confidence
