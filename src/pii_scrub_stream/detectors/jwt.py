"""JWT (JSON Web Token) detector.

JWTs follow the format: ``<header>.<payload>.<signature>`` where each segment
is a Base64url-encoded string. This detector identifies tokens that match
the structural pattern and optionally validates that the header decodes to
valid JSON with expected fields (``alg``, ``typ``).
"""

from __future__ import annotations

import base64
import json
import re
from typing import List

from pii_scrub_stream.detectors.base import Detector, Match

# A JWT consists of three Base64url segments separated by dots.
# Each segment contains alphanumeric chars plus - and _ (Base64url alphabet).
# Minimum realistic lengths: header ~20, payload ~20, signature ~20 chars.
_JWT_RE = re.compile(
    r"\b(eyJ[A-Za-z0-9_-]{10,})\."     # header — always starts with eyJ (base64 of '{"')
    r"(eyJ[A-Za-z0-9_-]{10,})\."        # payload — typically starts with eyJ too
    r"([A-Za-z0-9_-]{20,})\b",           # signature
)


def _b64url_decode(data: str) -> bytes:
    """Decode Base64url data with padding correction."""
    # Add padding if needed
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def _is_valid_jwt_header(header_b64: str) -> bool:
    """Check whether the header segment decodes to valid JSON with 'alg' field."""
    try:
        header = json.loads(_b64url_decode(header_b64))
        return isinstance(header, dict) and "alg" in header
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return False


class JWTDetector(Detector):
    """Detect JSON Web Tokens (JWTs) in text.

    JWTs are three Base64url-encoded segments separated by dots. The detector
    validates the structural pattern and optionally verifies the header decodes
    to JSON containing the ``alg`` field.
    """

    label = "JWT"
    default_confidence = 0.90

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        for m in _JWT_RE.finditer(text):
            full_token = m.group()
            header_segment = m.group(1)

            # Validate header for higher confidence
            if _is_valid_jwt_header(header_segment):
                confidence = 0.99
            else:
                confidence = self.default_confidence

            matches.append(
                Match(
                    start=m.start(),
                    end=m.end(),
                    value=full_token,
                    label=self.label,
                    confidence=confidence,
                    replacement=f"[{self.label}_REDACTED]",
                )
            )
        return matches
