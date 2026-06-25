"""Generic API key detector.

This is a catch-all detector for API keys, tokens, and secrets that don't
match a more specific detector. It uses two strategies:

1. **Context-based**: Looks for patterns like ``api_key = "..."`` or
   ``Authorization: Bearer ...`` and extracts the credential value.
2. **High-entropy strings**: Detects long alphanumeric strings that appear
   to have high entropy (i.e. look random), which is characteristic of
   machine-generated secrets.

This detector intentionally runs at *lower* confidence than the specialised
detectors so that more-specific matches take priority during overlap resolution.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from redactai.engine.detectors.base import Detector, Match

# Context-based patterns: key-value pairs in configs, environment variables, etc.
_KEY_VALUE_RE = re.compile(
    r"(?:api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|secret[_-]?key"
    r"|private[_-]?key|client[_-]?secret|token|bearer|password|passwd|credentials)"
    r"[\s]*[:=]\s*['\"]?"
    r"([A-Za-z0-9_\-/.+]{16,})"
    r"['\"]?",
    re.IGNORECASE,
)

# Bearer token in Authorization header
_BEARER_RE = re.compile(
    r"\bBearer\s+([A-Za-z0-9_\-/.+]{20,})\b",
)

# Generic high-entropy token patterns (hex, base64-like, etc.)
# Must be at least 32 characters to reduce false positives.
_HEX_TOKEN_RE = re.compile(
    r"\b([a-f0-9]{32,})\b",
)

# Common API key prefixes used by various services
_PREFIXED_KEY_RE = re.compile(
    r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,})\b"   # GitHub tokens
    r"|\b(glpat-[A-Za-z0-9_\-]{20,})\b"                    # GitLab tokens
    r"|\b(xox[bpsar]-[A-Za-z0-9\-]{10,})\b"                # Slack tokens
    r"|\b(SG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{22,})\b"  # SendGrid keys
    r"|\b(sq0[a-z]{3}-[A-Za-z0-9_\-]{22,})\b"              # Square keys
    r"|\b(rk_live_[A-Za-z0-9]{20,})\b"                     # Stripe restricted
    r"|\b(pk_live_[A-Za-z0-9]{20,})\b"                     # Stripe publishable
    r"|\b(sk_live_[A-Za-z0-9]{20,})\b",                    # Stripe secret
)


def _shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string.

    Higher values indicate more randomness, which is characteristic of
    machine-generated secrets and API keys.
    """
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length) for count in counts.values()
    )


class GenericAPIKeyDetector(Detector):
    """Detect generic API keys, tokens, and secrets via context and entropy.

    This is a broad-spectrum detector that catches credentials not covered
    by the specialised detectors. It uses contextual clues (config key names,
    Authorization headers) and entropy analysis to identify secrets.
    """

    label = "API_KEY"
    default_confidence = 0.80
    default_severity = "HIGH"

    #: Minimum Shannon entropy to consider a string a potential secret.
    min_entropy: float = 3.5

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        seen_spans: set = set()

        # 1. Prefixed keys from known services (highest confidence generic match)
        for m in _PREFIXED_KEY_RE.finditer(text):
            # The pattern uses alternation with groups — find the matched group
            for i in range(1, m.lastindex + 1 if m.lastindex else 1):
                value = m.group(i)
                if value is not None:
                    span = (m.start(i), m.end(i))
                    if span not in seen_spans:
                        seen_spans.add(span)
                        matches.append(
                            Match(
                                start=span[0],
                                end=span[1],
                                value=value,
                                label=self.label,
                                confidence=0.95,
                                replacement=f"[{self.label}_REDACTED]",
                            )
                        )
                    break

        # 2. Bearer tokens
        for m in _BEARER_RE.finditer(text):
            value = m.group(1)
            span = (m.start(1), m.end(1))
            if span not in seen_spans:
                seen_spans.add(span)
                matches.append(
                    Match(
                        start=span[0],
                        end=span[1],
                        value=value,
                        label=self.label,
                        confidence=0.90,
                        replacement=f"[{self.label}_REDACTED]",
                    )
                )

        # 3. Context-based key-value detection
        for m in _KEY_VALUE_RE.finditer(text):
            value = m.group(1)
            span = (m.start(1), m.end(1))
            if span not in seen_spans:
                entropy = _shannon_entropy(value)
                # Only flag high-entropy values to avoid false positives
                if entropy >= self.min_entropy:
                    seen_spans.add(span)
                    # Scale confidence with entropy
                    confidence = min(0.92, 0.75 + (entropy - self.min_entropy) * 0.05)
                    matches.append(
                        Match(
                            start=span[0],
                            end=span[1],
                            value=value,
                            label=self.label,
                            confidence=round(confidence, 2),
                            replacement=f"[{self.label}_REDACTED]",
                        )
                    )

        # 4. Long hex tokens (lowest confidence, last resort)
        for m in _HEX_TOKEN_RE.finditer(text):
            value = m.group(1)
            span = (m.start(1), m.end(1))
            if span not in seen_spans and len(value) >= 32:
                entropy = _shannon_entropy(value)
                if entropy >= self.min_entropy:
                    seen_spans.add(span)
                    matches.append(
                        Match(
                            start=span[0],
                            end=span[1],
                            value=value,
                            label=self.label,
                            confidence=0.75,
                            replacement=f"[{self.label}_REDACTED]",
                        )
                    )

        return matches
