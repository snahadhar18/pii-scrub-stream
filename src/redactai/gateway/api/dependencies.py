# mypy: ignore-errors
"""FastAPI dependency providers.

These functions bridge FastAPI's ``Depends`` system to our DI
:class:`Container`. Handlers declare what they need (a :class:`ScanService`, the
engine, the audit logger) and receive instances resolved from application state,
which is populated once during the lifespan startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from redactai.gateway.core.container import Container
from redactai.gateway.core.service import ScanService

if TYPE_CHECKING:  # pragma: no cover
    from redactai.gateway.observability.audit import AuditLogger
    from redactai.gateway.observability.health import HealthCheck
    from redactai.gateway.observability.metrics import MetricsRegistry
    from redactai.gateway.streaming.processor import ProcessingEngine


def get_container(request: Request) -> Container:
    """Return the application-scoped DI container."""
    return request.app.state.container


def get_scan_service(request: Request) -> ScanService:
    """Return the shared :class:`ScanService`."""
    return request.app.state.container.scan_service


def get_engine(request: Request) -> ProcessingEngine:
    """Return the shared, already-started processing engine."""
    return request.app.state.engine


def get_audit_logger(request: Request) -> AuditLogger:
    """Return the shared audit logger."""
    return request.app.state.audit


def get_metrics(request: Request) -> MetricsRegistry:
    """Return the shared metrics registry."""
    return request.app.state.metrics


def get_health(request: Request) -> HealthCheck:
    """Return the shared health-check registry."""
    return request.app.state.health


__all__ = [
    "get_container",
    "get_scan_service",
    "get_engine",
    "get_audit_logger",
    "get_metrics",
    "get_health",
]
