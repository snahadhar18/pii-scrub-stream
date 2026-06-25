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
from typing import List, Pattern


@dataclass(frozen=True)
class Match:
    """A single detected span of sensitive text.

    Attributes:
        start: Index of the first character of the match (inclusive).
        end: Index just past the last character of the match (exclusive).
        value: The raw matched substring.
        label: Machine-readable category, e.g. ``"EMAIL"`` or ``"SSN"``.
    """

    start: int
    end: int
    value: str
    label: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid match span: start={self.start}, end={self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start


class Detector(ABC):
    """Interface implemented by every detector.

    Subclasses must provide a unique ``label`` and implement :meth:`detect`.
    """

    #: Machine-readable category reported on every :class:`Match`.
    label: str = "GENERIC"

    @abstractmethod
    def detect(self, text: str) -> List[Match]:
        """Return all sensitive spans found in ``text``.

        Implementations must be pure (no mutation of shared state) so the
        engine can call them concurrently.
        """
        raise NotImplementedError

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

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        for m in self.pattern.finditer(text):
            value = m.group()
            if self.validate(value):
                matches.append(Match(m.start(), m.end(), value, self.label))
        return matches


def compile_pattern(pattern: str, flags: int = 0) -> Pattern[str]:
    """Compile ``pattern`` with sensible defaults; exposed for reuse/testing."""
    return re.compile(pattern, flags)
