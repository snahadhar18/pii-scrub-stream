"""Network secrets detector."""

import re

from redactai.engine.detectors.base import Detector, Match

_URI_PASSWORD_RE = re.compile(
    r"\b((?:mongodb|postgres|postgresql|redis|mysql|mssql|amqp|amqps)://"
    r"[^:/?#\s]+:([^@/?#\s]+)@[^/?#\s]+(?:/[^?#\s]*)?)\b"
)

_GENERIC_WEBHOOK_RE = re.compile(
    r"(https?://(?:[\w-]+\.)+[\w-]+(?:/[^/\s]+)*/webhooks?/[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+)"
)

class NetworkSecretsDetector(Detector):
    """Detect database connection strings with passwords and generic webhooks."""

    label = "NETWORK_SECRET"
    default_confidence = 0.90
    default_severity = "HIGH"

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        
        # Connection strings (capturing the entire string to redact or just the password)
        for m in _URI_PASSWORD_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="DB_CONNECTION_STRING", confidence=0.95,
                severity="CRITICAL", replacement="[DB_URI_REDACTED]"
            ))
            
        # Generic Webhooks
        for m in _GENERIC_WEBHOOK_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="WEBHOOK_URL", confidence=0.85,
                severity=self.default_severity, replacement="[WEBHOOK_REDACTED]"
            ))

        return matches
