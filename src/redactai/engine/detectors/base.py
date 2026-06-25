"""Core detector interface and reusable base classes.

A :class:`Detector` inspects a chunk of text and reports the spans that
contain sensitive information. Detectors are intentionally *stateless* with
respect to a single ``detect`` call so they can be shared safely across
threads by the redaction engine.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True)
class Match:
    """A single detected span of sensitive text.

    Attributes:
        start: Index of the first character of the match (inclusive).
        end: Index just past the last character of the match (exclusive).
        value: The raw matched substring.
        label: Machine-readable category, e.g. ``"EMAIL"`` or ``"SSN"``.
        confidence: Float between 0.0 and 1.0 indicating detection confidence.
        replacement: Suggested redaction placeholder, e.g. ``"[EMAIL_REDACTED]"``.
    """

    start: int
    end: int
    value: str
    label: str
    confidence: float = 1.0
    severity: str = "LOW"
    replacement: str = "[REDACTED]"

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid match span: start={self.start}, end={self.end}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @property
    def length(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict:
        """Serialize the match to a dictionary (useful for JSON output)."""
        return {
            "match": self.value,
            "type": self.label,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "severity": self.severity,
            "replacement": self.replacement,
        }


class Detector(ABC):
    """Interface implemented by every detector.

    Subclasses must provide a unique ``label`` and implement :meth:`detect`.
    """

    #: Machine-readable category reported on every :class:`Match`.
    label: str = "GENERIC"

    #: Default confidence score for detections.
    default_confidence: float = 0.95

    #: Default severity level for detections.
    default_severity: str = "LOW"

    @abstractmethod
    def detect(self, text: str) -> list[Match]:
        """Return all sensitive spans found in ``text``.

        Implementations must be pure (no mutation of shared state) so the
        engine can call them concurrently.
        """
        raise NotImplementedError

    @property
    def replacement_tag(self) -> str:
        """The placeholder tag used to replace detected values."""
        return f"[{self.label}_REDACTED]"

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(label={self.label!r})"


class RegexDetector(Detector):
    """Convenience base for detectors driven by a single regular expression.

    Subclasses set :attr:`pattern` (and optionally :attr:`label`) and may
    override :meth:`validate` to reject false positives (e.g. a Luhn check
    for credit-card numbers).
    """

    #: Compiled pattern used to locate candidate matches.
    pattern: Pattern[str]

    def __init__(self) -> None:
        if not hasattr(self, "pattern"):
            raise TypeError(f"{type(self).__name__} must define a 'pattern' attribute")

    def validate(self, value: str) -> bool:
        """Return ``True`` if ``value`` is a genuine match.

        The default accepts everything the regex matched. Override to add
        secondary validation.
        """
        return True

    def get_confidence(self, value: str) -> float:
        """Return a confidence score for the given matched value.

        Override in subclasses for context-dependent confidence scoring.
        The default returns :attr:`default_confidence`.
        """
        return self.default_confidence

    def get_severity(self, value: str) -> str:
        """Return a severity level for the given matched value.

        Override in subclasses for context-dependent severity scoring.
        The default returns :attr:`default_severity`.
        """
        return self.default_severity

    def detect(self, text: str) -> list[Match]:
        matches: list[Match] = []
        for m in self.pattern.finditer(text):
            value = m.group()
            if self.validate(value):
                confidence = self.get_confidence(value)
                severity = self.get_severity(value)
                matches.append(
                    Match(
                        start=m.start(),
                        end=m.end(),
                        value=value,
                        label=self.label,
                        confidence=confidence,
                        severity=severity,
                        replacement=self.replacement_tag,
                    )
                )
        return matches


def compile_pattern(pattern: str, flags: int = 0) -> Pattern[str]:
    """Compile ``pattern`` with sensible defaults; exposed for reuse/testing."""
    return re.compile(pattern, flags)
