"""Auth tokens detector."""

import re

from redactai.engine.detectors.base import Detector, Match

_ANTHROPIC_RE = re.compile(r"\b(sk-ant-api03-[A-Za-z0-9\-_]{93}AA)\b")
_DISCORD_BOT_RE = re.compile(r"\b([A-Za-z0-9_]{24,26}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,38})\b")
_DISCORD_WEBHOOK_RE = re.compile(r"(https?://discord\.com/api/webhooks/[0-9]+/[A-Za-z0-9_\-]+)")

class AuthTokensDetector(Detector):
    """Detect specific service authentication tokens."""

    label = "AUTH_TOKEN"
    default_confidence = 0.95
    default_severity = "CRITICAL"

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        
        # Anthropic
        for m in _ANTHROPIC_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="ANTHROPIC_KEY", confidence=0.99,
                severity=self.default_severity, replacement="[ANTHROPIC_KEY_REDACTED]"
            ))
            
        # Discord Bot
        for m in _DISCORD_BOT_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="DISCORD_BOT_TOKEN", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[DISCORD_TOKEN_REDACTED]"
            ))
            
        # Discord Webhook
        for m in _DISCORD_WEBHOOK_RE.finditer(text):
            matches.append(Match(
                start=m.start(1), end=m.end(1), value=m.group(1),
                label="DISCORD_WEBHOOK", confidence=self.default_confidence,
                severity=self.default_severity, replacement="[DISCORD_WEBHOOK_REDACTED]"
            ))

        return matches
