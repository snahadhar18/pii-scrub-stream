"""Secret detector."""

import re

from redactai.engine.detectors.base import Detector, Match
from redactai.engine.detectors.generic_api_key_detector import _shannon_entropy

_SECRET_CTX_RE = re.compile(
    r"(?:secret|client[_-]?secret|app[_-]?secret|api[_-]?secret)[\s]*[:=]\s*['\"]?"
    r"([A-Za-z0-9_\-/.+=]{16,128})"
    r"['\"]?",
    re.IGNORECASE,
)


class SecretDetector(Detector):
    """Detect generic secrets based on contextual clues and minimum length/entropy."""

    label = "SECRET"
    default_confidence = 0.85
    default_severity = "HIGH"

    min_entropy: float = 3.0

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        for m in _SECRET_CTX_RE.finditer(text):
            value = m.group(1)
            entropy = _shannon_entropy(value)

            if entropy >= self.min_entropy:
                confidence = min(
                    0.95, self.default_confidence + (entropy - self.min_entropy) * 0.05
                )
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
