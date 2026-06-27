"""AWS Access Key detector.

AWS Access Key IDs follow a well-defined format:
- Start with ``AKIA`` (long-term credentials) or ``ASIA`` (temporary/STS)
- Followed by exactly 16 uppercase alphanumeric characters

AWS Secret Access Keys are 40 characters of Base64-like characters.

This detector catches both key types with appropriate confidence levels.
"""

from __future__ import annotations

import re

from redactai.engine.detectors.base import Detector, Match

# AWS Access Key ID: starts with AKIA/ASIA/AIDA/AROA/ANPA/ANVA followed
# by 16 uppercase alphanumeric characters.
_AWS_ACCESS_KEY_RE = re.compile(r"\b((?:AKIA|ASIA|AIDA|AROA|ANPA|ANVA)[A-Z0-9]{16})\b")

# AWS Secret Access Key: 40 characters of Base64-like characters.
# Usually appears near an access key or in a config block.
_AWS_SECRET_KEY_RE = re.compile(
    r"(?:aws_secret_access_key|secret_?key|SECRET_KEY|aws_secret)"
    r"[\s:=]+['\"]?"
    r"([A-Za-z0-9/+=]{40})"
    r"['\"]?"
)


class AWSAccessKeyDetector(Detector):
    """Detect AWS Access Key IDs and Secret Access Keys.

    Access Key IDs (starting with ``AKIA``, ``ASIA``, etc.) are detected with
    high confidence due to their distinctive prefix. Secret keys are matched
    only when preceded by a recognisable config key name.
    """

    label = "AWS_KEY"
    default_confidence = 0.97
    default_severity = "CRITICAL"

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []

        # Detect Access Key IDs
        for m in _AWS_ACCESS_KEY_RE.finditer(text):
            value = m.group(1)
            prefix = value[:4]

            # AKIA = long-term, ASIA = STS temp creds — both high confidence
            confidence = 0.99 if prefix in ("AKIA", "ASIA") else 0.95

            matches.append(
                Match(
                    start=m.start(1),
                    end=m.end(1),
                    value=value,
                    label=self.label,
                    confidence=confidence,
                    replacement=f"[{self.label}_REDACTED]",
                )
            )

        # Detect Secret Access Keys (context-dependent)
        for m in _AWS_SECRET_KEY_RE.finditer(text):
            value = m.group(1)
            matches.append(
                Match(
                    start=m.start(1),
                    end=m.end(1),
                    value=value,
                    label="AWS_SECRET",
                    confidence=0.92,
                    replacement="[AWS_SECRET_REDACTED]",
                )
            )

        return matches
