# mypy: ignore-errors
"""Detector plugin registry -- where external detection logic plugs in.

Detectors are *never* hardcoded. They are registered here, either:

* programmatically via :meth:`DetectorRegistry.register`, or
* through Python entry points in the ``redactai.gateway.detectors`` group, which
  lets a separately-installed package (the team building the actual detection
  logic) expose its detectors with zero code changes here.

The registry stores zero-argument *factories* so detectors are instantiated
lazily and per-container, keeping configuration and lifetime concerns out of
the plugins themselves.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from redactai.gateway.core.detector import DetectorProtocol
from redactai.gateway.core.exceptions import DetectorError

logger = logging.getLogger(__name__)

DetectorFactory = Callable[[], DetectorProtocol]

#: Entry-point group external detector packages should advertise.
ENTRY_POINT_GROUP = "redactai.gateway.detectors"


class DetectorRegistry:
    """A name -> factory registry for pluggable detectors."""

    def __init__(self) -> None:
        self._factories: dict[str, DetectorFactory] = {}

    def register(self, name: str, factory: DetectorFactory, *, replace: bool = False) -> None:
        """Register ``factory`` under ``name``.

        Args:
            name: Unique, CLI/config-friendly identifier.
            factory: Zero-arg callable returning a detector instance.
            replace: Allow overwriting an existing registration.

        Raises:
            DetectorError: if ``name`` is already registered and not replacing.
        """
        if name in self._factories and not replace:
            raise DetectorError(f"detector already registered: {name!r}")
        self._factories[name] = factory
        logger.debug("registered detector %r", name)

    def unregister(self, name: str) -> None:
        """Remove a registration if present (idempotent)."""
        self._factories.pop(name, None)

    def names(self) -> list[str]:
        """Return the sorted list of registered detector names."""
        return sorted(self._factories)

    def __contains__(self, name: object) -> bool:
        return name in self._factories

    def create(self, name: str) -> DetectorProtocol:
        """Instantiate the detector registered under ``name``."""
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise DetectorError(
                f"unknown detector {name!r}; available: {', '.join(self.names()) or '<none>'}"
            ) from exc
        detector = factory()
        if not isinstance(detector, DetectorProtocol):
            raise DetectorError(
                f"factory for {name!r} returned an object without a detect() method"
            )
        return detector

    def create_many(self, names: list[str]) -> list[DetectorProtocol]:
        """Instantiate several detectors, preserving order."""
        return [self.create(n) for n in names]

    def create_all(self) -> list[DetectorProtocol]:
        """Instantiate one of every registered detector."""
        return [self.create(n) for n in self.names()]

    def load_entry_points(self, group: str = ENTRY_POINT_GROUP) -> int:
        """Discover detectors advertised by installed packages.

        Returns the number of newly registered detectors. Failures to load an
        individual plugin are logged and skipped so one broken plugin never
        takes down the whole gateway.
        """
        from importlib import metadata

        loaded = 0
        try:
            entry_points = metadata.entry_points(group=group)
        except TypeError:  # pragma: no cover - Python < 3.10 fallback
            entry_points = metadata.entry_points().get(group, [])  # type: ignore[attr-defined]
        for ep in entry_points:
            try:
                factory = ep.load()
                self.register(ep.name, factory, replace=True)
                loaded += 1
            except Exception:  # noqa: BLE001 - isolate broken plugins
                logger.exception("failed to load detector entry point %r", ep.name)
        return loaded


#: Process-wide default registry. Tests and embedders may create their own.
global_registry = DetectorRegistry()

# Auto-register built-in detectors from the engine
try:
    from redactai.engine.detectors import REGISTRY as ENGINE_REGISTRY
    from redactai.gateway.core.detector import DetectionSpan, DetectorProtocol

    class _EngineAdapter(DetectorProtocol):
        def __init__(self, engine_cls):
            self._detector = engine_cls()

        def detect(self, text: str) -> list[DetectionSpan]:
            matches = self._detector.detect(text)
            return [
                DetectionSpan(
                    start=m.start,
                    end=m.end,
                    label=m.label,
                    text=m.value,
                    confidence=m.confidence,
                    replacement=m.replacement,
                )
                for m in matches
            ]

    for _name, _cls in ENGINE_REGISTRY.items():
        # Register a factory that returns the adapted engine detector
        def _factory(c=_cls):
            return _EngineAdapter(c)
        global_registry.register(_name, _factory, replace=True)
except ImportError:
    pass

__all__ = ["DetectorRegistry", "DetectorFactory", "global_registry", "ENTRY_POINT_GROUP"]
