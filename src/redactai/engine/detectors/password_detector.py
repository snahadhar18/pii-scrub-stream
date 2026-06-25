"""Password detector."""

import re

from redactai.engine.detectors.base import Detector, Match
from redactai.engine.detectors.generic_api_key_detector import _shannon_entropy

_PASSWORD_CTX_RE = re.compile(
    r"(?:password|passwd|pwd)[\s]*[:=]\s*['\"]?"
    r"([^'\"\s\\]{8,64})"
    r"['\"]?",
    re.IGNORECASE,
)

class PasswordDetector(Detector):
    """Detect passwords based on contextual clues and minimum length."""

    label = "PASSWORD"
    default_confidence = 0.85
    default_severity = "CRITICAL"

    min_entropy: float = 2.5

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        for m in _PASSWORD_CTX_RE.finditer(text):
            value = m.group(1)
            entropy = _shannon_entropy(value)
            
            # Require minimum entropy to avoid flagging password=test or empty values
            if entropy >= self.min_entropy:
                confidence = min(0.95, self.default_confidence + (entropy - self.min_entropy) * 0.05)
                matches.append(
                    Match(
                        start=m.start(1),
                        end=m.end(1),
                        value=value,
                        label=self.label,
                        confidence=round(confidence, 2),
                        severity=self.default_severity,
                        replacement=self.replacement_tag,
                    )
                )
        return matches
