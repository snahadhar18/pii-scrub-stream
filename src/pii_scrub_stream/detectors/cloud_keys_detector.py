"""Cloud keys detector."""

import re
from typing import List

from pii_scrub_stream.detectors.base import Detector, Match

_GCP_API_KEY_RE = re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")
_GCP_OAUTH_RE = re.compile(r"\b(ya29\.[0-9A-Za-z\-_]+)\b")
_AZURE_STORAGE_RE = re.compile(
    r"\b(AccountKey=[A-Za-z0-9+/=]{86,})\b", re.IGNORECASE
)

class CloudKeysDetector(Detector):
    """Detect Google Cloud and Azure keys and secrets."""

    label = "CLOUD_KEY"
    default_confidence = 0.95
    default_severity = "CRITICAL"

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        
        # GCP API Keys
        for m in _GCP_API_KEY_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="GCP_API_KEY", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[GCP_API_KEY_REDACTED]"
            ))
            
        # GCP OAuth Tokens
        for m in _GCP_OAUTH_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="GCP_OAUTH_TOKEN", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[GCP_OAUTH_REDACTED]"
            ))
            
        # Azure Storage Account Keys
        for m in _AZURE_STORAGE_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="AZURE_STORAGE_KEY", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[AZURE_KEY_REDACTED]"
            ))

        return matches
