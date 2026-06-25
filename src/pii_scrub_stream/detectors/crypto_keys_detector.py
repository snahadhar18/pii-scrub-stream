"""Crypto keys detector."""

import re
from typing import List

from pii_scrub_stream.detectors.base import Detector, Match

_PRIVATE_KEY_RE = re.compile(
    r"(-----BEGIN (?:RSA |DSA |EC |OPENSSH |)[ ]?PRIVATE KEY-----"
    r"(?:\s|\S){1,3000}?"
    r"-----END (?:RSA |DSA |EC |OPENSSH |)[ ]?PRIVATE KEY-----)"
)

class CryptoKeysDetector(Detector):
    """Detect Private Keys (PEM format) and SSH keys."""

    label = "CRYPTO_KEY"
    default_confidence = 0.99
    default_severity = "CRITICAL"

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        
        for m in _PRIVATE_KEY_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="PRIVATE_KEY", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[PRIVATE_KEY_REDACTED]"
            ))

        return matches
