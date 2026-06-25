"""HTTP API layer (FastAPI).

Exposes the gateway over HTTP: synchronous scanning, streaming, file ingestion,
health and metrics. The API is a thin adapter -- it validates input, delegates to
the core services resolved from the DI :class:`Container`, and serializes
results. No detection or business logic lives here.

``create_app`` is imported lazily so the rest of the package (and its tests) do
not require FastAPI to be installed.
"""

from __future__ import annotations

__all__ = ["create_app"]


def create_app(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
    """Lazily import and build the FastAPI application.

    Importing here (rather than at module load) keeps ``fastapi`` an optional
    dependency for users who only need the CLI/library.
    """
    from redactai.gateway.api.app import create_app as _create_app

    return _create_app(*args, **kwargs)
