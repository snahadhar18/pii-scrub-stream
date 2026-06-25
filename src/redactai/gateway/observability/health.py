"""Health checks for liveness/readiness probes.

A :class:`HealthCheck` aggregates named boolean probes into a single
:class:`HealthReport` consumable by the ``/health`` endpoint, Docker
``HEALTHCHECK`` and Kubernetes probes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum


class HealthStatus(str, Enum):
    """Overall health verdict."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthReport:
    """Result of evaluating all registered probes."""

    status: HealthStatus
    checks: Mapping[str, bool]
    version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "checks": dict(self.checks),
            "version": self.version,
        }


class HealthCheck:
    """Registry of named probes evaluated on demand.

    A probe is any zero-arg callable returning ``True`` when healthy. Probes
    that raise are treated as failing (and never propagate).
    """

    def __init__(self, version: str = "0.0.0") -> None:
        self.version = version
        self._probes: dict[str, Callable[[], bool]] = {}

    def add(self, name: str, probe: Callable[[], bool]) -> None:
        """Register a probe under ``name``."""
        self._probes[name] = probe

    def run(self) -> HealthReport:
        """Evaluate every probe and produce an aggregate report."""
        results: dict[str, bool] = {}
        for name, probe in self._probes.items():
            try:
                results[name] = bool(probe())
            except Exception:  # noqa: BLE001 - a failing probe is just unhealthy
                results[name] = False
        if not results or all(results.values()):
            status = HealthStatus.HEALTHY
        elif any(results.values()):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        return HealthReport(status=status, checks=results, version=self.version)


__all__ = ["HealthStatus", "HealthReport", "HealthCheck"]
