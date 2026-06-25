"""Redaction -- turning detected spans into safe output text.

Redaction is pure string transformation infrastructure: given the spans a
detector produced, replace those regions of the original text. It contains no
detection logic of its own.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from enum import Enum

from redactai.gateway.core.detector import DetectionSpan


class RedactionStrategy(str, Enum):
    """How a detected span should be rewritten."""

    #: Replace with the span's ``replacement`` or ``[LABEL]``.
    TAG = "tag"
    #: Replace every character with ``mask_char`` (preserves length).
    MASK = "mask"
    #: Replace with ``[LABEL:<short sha256>]`` for correlation without exposure.
    HASH = "hash"
    #: Delete the span entirely.
    REMOVE = "remove"


class Redactor:
    """Applies a :class:`RedactionStrategy` to text given detected spans.

    The redactor resolves overlapping spans by keeping the higher-confidence
    (then longer) span, then rewrites the text in a single right-to-left pass so
    earlier offsets stay valid.
    """

    def __init__(
        self,
        strategy: RedactionStrategy = RedactionStrategy.TAG,
        *,
        mask_char: str = "*",
        hash_length: int = 8,
    ) -> None:
        self.strategy = RedactionStrategy(strategy)
        self.mask_char = mask_char
        self.hash_length = hash_length

    def redact(self, text: str, spans: Sequence[DetectionSpan]) -> str:
        """Return ``text`` with every span rewritten per the strategy."""
        if not spans:
            return text
        ordered = self._resolve_overlaps(spans)
        # Apply from the end so earlier indices remain valid after edits.
        out = text
        for span in sorted(ordered, key=lambda s: s.start, reverse=True):
            out = out[: span.start] + self._replacement_for(span) + out[span.end :]
        return out

    def _replacement_for(self, span: DetectionSpan) -> str:
        if self.strategy is RedactionStrategy.REMOVE:
            return ""
        if self.strategy is RedactionStrategy.MASK:
            return self.mask_char * span.length
        if self.strategy is RedactionStrategy.HASH:
            digest = hashlib.sha256(span.text.encode("utf-8")).hexdigest()[: self.hash_length]
            return f"[{span.label}:{digest}]"
        # TAG (default)
        return span.replacement or f"[{span.label}]"

    @staticmethod
    def _resolve_overlaps(spans: Sequence[DetectionSpan]) -> list[DetectionSpan]:
        """Drop spans that overlap a previously accepted, higher-priority span."""
        ranked = sorted(spans, key=lambda s: (-s.confidence, -(s.end - s.start), s.start))
        accepted: list[DetectionSpan] = []
        for span in ranked:
            if not any(span.start < a.end and a.start < span.end for a in accepted):
                accepted.append(span)
        return accepted


__all__ = ["RedactionStrategy", "Redactor"]
