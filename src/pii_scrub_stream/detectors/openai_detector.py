"""OpenAI API key detector.

OpenAI API keys use well-known prefixes:
- ``sk-`` for standard secret keys (legacy format: ``sk-`` + 48 alphanum chars)
- ``sk-proj-`` for project-scoped keys (newer format, variable length)
- ``sk-svcacct-`` for service account keys

This detector matches these prefixes followed by a sequence of alphanumeric
characters, hyphens, and underscores of reasonable length.
"""

from __future__ import annotations

import re
from typing import List

from pii_scrub_stream.detectors.base import Detector, Match

# OpenAI key patterns:
#  - Legacy:    sk-<48 alphanumeric chars>
#  - Project:   sk-proj-<variable length alphanum+hyphens+underscores>
#  - SvcAcct:   sk-svcacct-<variable length>
#  - Org keys:  org-<24+ chars>
_OPENAI_KEY_RE = re.compile(
    r"\b(sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,})\b"
)

# Organization ID pattern (less sensitive but still a credential leak)
_OPENAI_ORG_RE = re.compile(
    r"\b(org-[A-Za-z0-9]{20,})\b"
)


class OpenAIKeyDetector(Detector):
    """Detect OpenAI API keys (``sk-...``) and organisation IDs (``org-...``).

    Project-scoped keys (``sk-proj-``) and service account keys (``sk-svcacct-``)
    are detected with the highest confidence. Legacy ``sk-`` keys are also
    high confidence. Organisation IDs are slightly lower confidence since the
    ``org-`` prefix is less distinctive.
    """

    label = "OPENAI_KEY"
    default_confidence = 0.97
    default_severity = "CRITICAL"

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []

        for m in _OPENAI_KEY_RE.finditer(text):
            value = m.group(1)

            # Project and service-account keys have highly distinctive prefixes
            if value.startswith("sk-proj-") or value.startswith("sk-svcacct-"):
                confidence = 0.99
            elif value.startswith("sk-"):
                # Standard sk- key — still high confidence given the length
                confidence = 0.97
            else:
                confidence = self.default_confidence

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

        for m in _OPENAI_ORG_RE.finditer(text):
            value = m.group(1)
            matches.append(
                Match(
                    start=m.start(1),
                    end=m.end(1),
                    value=value,
                    label="OPENAI_ORG",
                    confidence=0.85,
                    replacement="[OPENAI_ORG_REDACTED]",
                )
            )

        return matches
