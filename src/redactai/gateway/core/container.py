"""Dependency-injection container -- the composition root.

The :class:`Container` is the *only* place that knows how to wire concrete
implementations together from :class:`Settings`. Every other module receives its
collaborators by argument, never reaching for globals. This keeps the system
testable (swap any provider in a test) and makes the dependency graph explicit.

Providers are lazily constructed and memoized so the container behaves like a
lightweight singleton scope for the lifetime of a request handler, CLI command
or worker process.
"""

from __future__ import annotations

import logging
from functools import cached_property

from redactai.gateway.config.settings import Settings, get_settings
from redactai.gateway.core.detector import DetectorProtocol, NullDetector
from redactai.gateway.core.redaction import Redactor
from redactai.gateway.core.registry import DetectorRegistry, global_registry
from redactai.gateway.core.service import ScanService

logger = logging.getLogger(__name__)


class Container:
    """Composition root that builds and caches application services."""

    def __init__(
        self,
        settings: Settings | None = None,
        registry: DetectorRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or global_registry
        if self.settings.load_entry_point_detectors:
            count = self.registry.load_entry_points()
            if count:
                logger.info("loaded %d detector(s) from entry points", count)

    # --- providers -------------------------------------------------------
    @cached_property
    def detectors(self) -> list[DetectorProtocol]:
        """Resolve the configured detectors from the registry.

        Falls back to a single :class:`NullDetector` when nothing is registered
        so the infrastructure still runs end-to-end without any plugin.
        """
        names = list(self.settings.detectors)
        if names:
            resolved = self.registry.create_many(names)
        elif self.registry.names():
            resolved = self.registry.create_all()
        else:
            logger.warning("no detectors registered; using NullDetector (no-op)")
            resolved = [NullDetector()]
        return resolved

    @cached_property
    def redactor(self) -> Redactor:
        """The redactor configured by the processing settings."""
        return Redactor(self.settings.processing.redaction_strategy)

    @cached_property
    def scan_service(self) -> ScanService:
        """The fully-wired :class:`ScanService`."""
        return ScanService(self.detectors, self.redactor)

    def build_engine(self):  # type: ignore[no-untyped-def]
        """Create a fresh processing engine bound to this container's service.

        Returns a new engine each call (engines own a thread pool and should be
        used as context managers), unlike the memoized service providers.
        """
        from redactai.gateway.streaming.processor import ProcessingEngine

        return ProcessingEngine(
            self.scan_service,
            workers=self.settings.processing.workers,
            batch_size=self.settings.processing.batch_size,
            queue_maxsize=self.settings.processing.queue_maxsize,
            max_retries=self.settings.processing.max_retries,
            redact=self.settings.processing.redact_by_default,
        )

    def ingestion_factory(self):  # type: ignore[no-untyped-def]
        """Return the ingestion source factory bound to ingestion settings."""
        from redactai.gateway.ingestion.factory import SourceFactory

        return SourceFactory(self.settings.ingestion)


__all__ = ["Container"]
