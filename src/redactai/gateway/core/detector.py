"""The detector contract -- the single seam between infrastructure and detection.

RedactAI owns everything *around* detection but never the detection itself.
Every detector is an external plugin that satisfies this contract::

    class Detector:
        def detect(self, text: str) -> Sequence[DetectionSpan]:
            ...

Two flavours of the contract are exposed:

* :class:`DetectorProtocol` -- a structural (duck-typed) :class:`typing.Protocol`
  so *any* object with a ``detect(text)`` method qualifies, including plain
  functions wrapped by :class:`CallableDetector`. This keeps integration with
  third-party detectors friction-free.
* :class:`Detector` -- a nominal abstract base class for plugins that want the
  shared scaffolding (a ``name``/``labels`` descriptor and ``__repr__``).

The engine only ever depends on the *protocol*, so detection logic stays fully
pluggable and is never hardcoded anywhere in this package.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class DetectionSpan:
    """An immutable region of ``text`` flagged by a detector.

    The span is intentionally lightweight (a frozen, slotted dataclass rather
    than a Pydantic model) because it sits on the hottest code path: detectors
    may emit millions of these per second. Validation of untrusted input is the
    job of the API boundary (:mod:`redactai.gateway.api.schemas`), not this type.

    Attributes:
        start: Index of the first matched character (inclusive).
        end: Index just past the last matched character (exclusive).
        label: Machine-readable category, e.g. ``"EMAIL"`` (detector-defined).
        text: The raw substring that was matched.
        confidence: Detector-supplied confidence in ``[0.0, 1.0]``.
        replacement: Optional placeholder used by the redactor. When ``None``
            the redactor falls back to its configured strategy.
    """

    start: int
    end: int
    label: str
    text: str
    confidence: float = 1.0
    replacement: str | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid span: start={self.start}, end={self.end}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")

    @property
    def length(self) -> int:
        """Number of characters covered by the span."""
        return self.end - self.start


@runtime_checkable
class DetectorProtocol(Protocol):
    """Structural contract every detector must satisfy.

    Any object exposing ``detect(text: str) -> Sequence[DetectionSpan]`` is a
    valid detector. The engine depends only on this protocol.
    """

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        """Return all sensitive spans found in ``text``.

        Implementations MUST be pure and thread-safe: the processing engine may
        invoke ``detect`` concurrently from many worker threads on the same
        instance.
        """
        ...


class Detector(ABC):
    """Optional nominal base class for detector plugins.

    Plugins are free to implement :class:`DetectorProtocol` directly, but
    subclassing :class:`Detector` provides a consistent ``name`` and a sensible
    ``__repr__`` for logging and the ``detectors`` CLI listing.
    """

    #: Human/machine-readable identifier surfaced in CLI listings and metrics.
    name: str = "detector"

    #: Labels this detector may emit; advisory metadata for documentation/UX.
    labels: tuple[str, ...] = ()

    @abstractmethod
    def detect(self, text: str) -> Sequence[DetectionSpan]:  # noqa: D401
        """Return all sensitive spans found in ``text`` (see protocol)."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(name={self.name!r})"


class NullDetector(Detector):
    """A detector that never matches anything.

    Used as the safe default when no plugins are configured so the rest of the
    infrastructure (engine, API, streaming) can be exercised end-to-end without
    pulling in any detection implementation. This is *not* detection logic; it
    is the absence of it.
    """

    name = "null"

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        return ()


class CallableDetector(Detector):
    """Adapter that turns a plain ``fn(text) -> spans`` callable into a detector.

    Lets integrators register a bare function as a plugin without authoring a
    class, while still benefiting from the registry and engine machinery.
    """

    def __init__(
        self,
        fn: Callable[[str], Iterable[DetectionSpan]],
        *,
        name: str = "callable",
        labels: Sequence[str] = (),
    ) -> None:
        self._fn = fn
        self.name = name
        self.labels = tuple(labels)

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        return tuple(self._fn(text))


__all__ = [
    "DetectionSpan",
    "DetectorProtocol",
    "Detector",
    "NullDetector",
    "CallableDetector",
]
