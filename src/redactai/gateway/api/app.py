"""FastAPI application factory and route definitions.

Endpoints:

* ``POST /scan``    -- scan a single text payload.
* ``POST /stream``  -- scan many lines, response streamed as JSON lines.
* ``POST /ingest``  -- upload a TXT/LOG/CSV/JSON file; scan it; return a summary.
* ``GET  /health``  -- liveness/readiness probe.
* ``GET  /metrics`` -- Prometheus (text) or JSON metrics snapshot.

The app is assembled via ``create_app`` so tests and deployments can inject a
custom :class:`Container`. A lifespan context wires shared, long-lived
collaborators (engine thread pool, audit logger) and tears them down cleanly.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from redactai.gateway.api.dependencies import (
    get_audit_logger,
    get_engine,
    get_health,
    get_metrics,
    get_scan_service,
)
from redactai.gateway.api.errors import register_error_handlers
from redactai.gateway.api.schemas import (
    HealthResponse,
    IngestResponse,
    ScanRequest,
    ScanResponse,
    StreamRequest,
)
from redactai.gateway.config.settings import Settings, get_settings
from redactai.gateway.core.container import Container
from redactai.gateway.core.models import Record
from redactai.gateway.core.service import ScanService
from redactai.gateway.ingestion.factory import SourceType
from redactai.gateway.observability.audit import AuditEvent, AuditLogger
from redactai.gateway.observability.health import HealthCheck
from redactai.gateway.observability.logging_config import configure_logging
from redactai.gateway.observability.metrics import MetricsRegistry
from redactai.gateway.streaming.processor import ProcessingEngine


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    """Build and return a configured FastAPI application."""
    settings = settings or get_settings()
    container = container or Container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.observability.log_level, settings.observability.log_format)
        engine = container.build_engine()
        engine.start()
        audit = AuditLogger(
            settings.observability.audit_path,
            enabled=settings.observability.audit_enabled,
        )
        health = HealthCheck(version=_version())
        health.add("detectors", lambda: len(container.scan_service.detectors) > 0)
        health.add("engine", lambda: engine._executor is not None)  # noqa: SLF001
        app.state.container = container
        app.state.settings = settings
        app.state.engine = engine
        app.state.audit = audit
        app.state.health = health
        app.state.metrics = engine.metrics
        try:
            yield
        finally:
            engine.shutdown(wait=True)
            audit.close()

    app = FastAPI(
        title=settings.api.title,
        version=_version(),
        description="Infrastructure gateway for pluggable PII/secret detection.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:
    @app.post("/scan", response_model=ScanResponse, tags=["scan"])
    async def scan(
        payload: ScanRequest,
        service: ScanService = Depends(get_scan_service),
        audit: AuditLogger = Depends(get_audit_logger),
    ) -> ScanResponse:
        """Scan a single text payload and optionally return redacted output."""
        record = Record(id="api", content=payload.text, source="api")
        result = service.scan(record, redact=payload.redact)
        audit.emit(
            AuditEvent(
                action="scan",
                record_id=result.record_id,
                source=result.source,
                hit_count=result.hit_count,
                label_counts=_label_counts(result.labels, result),
                actor="api",
            )
        )
        return ScanResponse.from_result(result)

    @app.post("/stream", tags=["scan"])
    async def stream(
        payload: StreamRequest,
        engine: ProcessingEngine = Depends(get_engine),
    ) -> StreamingResponse:
        """Scan many lines; results are streamed back as JSON Lines."""
        records = (
            Record(id=f"api:{i}", content=line, source="api", offset=i)
            for i, line in enumerate(payload.lines, start=1)
        )

        def generate() -> AsyncIterator[str]:  # type: ignore[misc]
            for result in engine.process(records):
                yield json.dumps(ScanResponse.from_result(result).model_dump()) + "\n"

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    @app.post("/ingest", response_model=IngestResponse, tags=["ingest"])
    async def ingest(
        request: Request,
        file: UploadFile = File(...),
        source_type: str | None = Query(
            default=None, description="Force text|csv|json; inferred from filename otherwise."
        ),
        redact: bool = Query(default=False),
        engine: ProcessingEngine = Depends(get_engine),
    ) -> IngestResponse:
        """Upload a TXT/LOG/CSV/JSON file, scan every record, return a summary."""
        container: Container = request.app.state.container
        factory = container.ingestion_factory()
        st = SourceType(source_type) if source_type else None
        suffix = Path(file.filename or "upload.txt").suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        try:
            engine.redact = redact
            with factory.for_path(tmp_path, st) as source:
                _, summary = engine.run(source.read_records())
        finally:
            tmp_path.unlink(missing_ok=True)
        return IngestResponse(
            source=file.filename or "upload",
            records=summary.records,
            spans=summary.spans,
            duration_ms=summary.duration_ms,
            errors=summary.errors,
            label_counts=summary.label_counts,
        )

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    async def health(check: HealthCheck = Depends(get_health)) -> HealthResponse:
        """Return aggregate service health."""
        report = check.run()
        return HealthResponse(
            status=report.status.value, version=report.version, checks=report.checks
        )

    @app.get("/metrics", tags=["ops"])
    async def get_metrics_endpoint(
        request: Request,
        fmt: str = Query(default="prometheus", pattern="^(prometheus|json)$"),
        registry: MetricsRegistry = Depends(get_metrics),
    ):  # type: ignore[no-untyped-def]
        """Expose metrics as Prometheus text (default) or JSON."""
        if fmt == "json":
            return registry.snapshot()
        return PlainTextResponse(registry.render_prometheus(), media_type="text/plain")


def _label_counts(labels: tuple[str, ...], result: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for span in getattr(result, "spans", ()):  # type: ignore[attr-defined]
        counts[span.label] = counts.get(span.label, 0) + 1
    return counts


def _version() -> str:
    from redactai.gateway import __version__

    return __version__


__all__ = ["create_app"]
