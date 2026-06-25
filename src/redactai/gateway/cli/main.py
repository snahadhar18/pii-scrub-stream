"""``redactai`` command-line entry point.

Commands:

* ``scan``      -- scan a file and write redacted output or a JSON report.
* ``stream``    -- filter a live stdin stream (``tail -f app.log | redactai stream``).
* ``ingest``    -- scan a file and print an aggregate summary.
* ``detectors`` -- list detector plugins currently registered.
* ``serve``     -- run the FastAPI service via uvicorn.

The CLI is a thin shell over the DI :class:`Container`; it never touches
detection logic directly.
"""

from __future__ import annotations

import json
import sys

import click

from redactai.gateway import __version__
from redactai.gateway.config.settings import get_settings
from redactai.gateway.core.container import Container
from redactai.gateway.observability.logging_config import configure_logging


def _build_container(detectors: tuple[str, ...], workers: int | None) -> Container:
    settings = get_settings().model_copy(deep=True)
    if detectors:
        settings.detectors = detectors
    if workers is not None:
        settings.processing.workers = workers
    return Container(settings)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="redactai")
@click.option("--log-level", default="WARNING", show_default=True, help="Logging verbosity.")
@click.option(
    "--log-format",
    type=click.Choice(["json", "text"]),
    default="text",
    show_default=True,
)
def cli(log_level: str, log_format: str) -> None:
    """RedactAI -- pluggable AI security gateway infrastructure."""
    configure_logging(log_level, log_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("-d", "--detector", "detectors", multiple=True, help="Enable a registered detector.")
@click.option("--type", "source_type", type=click.Choice(["text", "csv", "json"]), default=None)
@click.option("--redact/--no-redact", default=True, show_default=True)
@click.option("-w", "--workers", type=int, default=None, help="Override worker count.")
@click.option(
    "-o", "--output", type=click.Path(dir_okay=False), default=None, help="Redacted output file."
)
def scan(
    path: str,
    detectors: tuple[str, ...],
    source_type: str | None,
    redact: bool,
    workers: int | None,
    output: str | None,
) -> None:
    """Scan a file; write redacted output (or a JSON report with --no-redact)."""
    from redactai.gateway.ingestion.factory import SourceType

    container = _build_container(detectors, workers)
    factory = container.ingestion_factory()
    st = SourceType(source_type) if source_type else None
    out = open(output, "w", encoding="utf-8") if output else sys.stdout  # noqa: SIM115
    try:
        with container.build_engine() as engine:
            engine.redact = redact
            with factory.for_path(path, st) as source:
                for result in engine.process(source.read_records()):
                    if redact:
                        out.write((result.redacted or "") + "\n")
                    else:
                        out.write(
                            json.dumps(
                                {
                                    "record_id": result.record_id,
                                    "hits": result.hit_count,
                                    "labels": list(result.labels),
                                }
                            )
                            + "\n"
                        )
    finally:
        if output:
            out.close()


@cli.command()
@click.option("-d", "--detector", "detectors", multiple=True, help="Enable a registered detector.")
@click.option("--redact/--no-redact", default=True, show_default=True)
@click.option("-w", "--workers", type=int, default=None, help="Override worker count.")
@click.option("--buffer-size", type=int, default=None, help="Override in-flight buffer size.")
def stream(
    detectors: tuple[str, ...], redact: bool, workers: int | None, buffer_size: int | None
) -> None:
    """Filter a live stream from stdin to stdout in real time."""
    from redactai.gateway.streaming.stream import StreamProcessor

    container = _build_container(detectors, workers)
    engine = container.build_engine()
    if buffer_size is not None:
        engine.queue_maxsize = buffer_size
    engine.redact = redact
    processor = StreamProcessor(engine, emit_redacted=redact)
    processor.run(sys.stdin, sys.stdout)


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("-d", "--detector", "detectors", multiple=True, help="Enable a registered detector.")
@click.option("--type", "source_type", type=click.Choice(["text", "csv", "json"]), default=None)
@click.option("-w", "--workers", type=int, default=None, help="Override worker count.")
def ingest(
    path: str, detectors: tuple[str, ...], source_type: str | None, workers: int | None
) -> None:
    """Scan a file and print an aggregate JSON summary."""
    from redactai.gateway.ingestion.factory import SourceType

    container = _build_container(detectors, workers)
    factory = container.ingestion_factory()
    st = SourceType(source_type) if source_type else None
    with container.build_engine() as engine, factory.for_path(path, st) as source:
        _, summary = engine.run(source.read_records())
    click.echo(
        json.dumps(
            {
                "records": summary.records,
                "spans": summary.spans,
                "errors": summary.errors,
                "duration_ms": round(summary.duration_ms, 2),
                "throughput_rps": round(summary.throughput_rps, 1),
                "label_counts": dict(summary.label_counts),
            },
            indent=2,
        )
    )


@cli.command()
def detectors() -> None:
    """List detector plugins currently registered."""
    container = Container(get_settings())
    names = container.registry.names()
    if not names:
        click.echo("No detectors registered. Install a detector plugin or register one.")
        return
    for name in names:
        click.echo(name)


@cli.command()
@click.option("--host", default=None, help="Bind host (defaults to config).")
@click.option("--port", type=int, default=None, help="Bind port (defaults to config).")
@click.option("--reload", is_flag=True, default=False, help="Enable autoreload (dev only).")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Run the FastAPI service with uvicorn."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise click.ClickException(
            "uvicorn is not installed; install with: pip install 'redactai[api]'"
        ) from exc
    settings = get_settings()
    uvicorn.run(
        "redactai.gateway.api.app:create_app",
        factory=True,
        host=host or settings.api.host,
        port=port or settings.api.port,
        reload=reload,
    )


if __name__ == "__main__":  # pragma: no cover
    cli()
