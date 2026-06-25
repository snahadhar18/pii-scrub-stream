"""Command-line interface for redactai (built with Click)."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import click

from redactai.engine import __version__
from redactai.engine.detectors import (
    available_detectors,
    build_detectors,
    default_detectors,
)
from redactai.engine.detectors.base import Detector
from redactai.engine.scrubber.engine import FileResult, RedactionEngine
from redactai.engine.scrubber.redaction import Redactor, label_redactor, make_mask_redactor

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _select_detectors(names: Sequence[str]) -> list[Detector]:
    """Resolve CLI ``--detector`` options into detector instances."""
    if not names:
        return default_detectors()
    try:
        return build_detectors(list(names))
    except KeyError as exc:
        raise click.BadParameter(str(exc)) from exc


def _select_redactor(mask: bool, keep_last: int) -> Redactor:
    if mask:
        return make_mask_redactor(keep_last=keep_last)
    return label_redactor


def _build_engine(
    detector_names: Sequence[str],
    mask: bool,
    keep_last: int,
) -> RedactionEngine:
    detectors = _select_detectors(detector_names)
    redactor = _select_redactor(mask, keep_last)
    return RedactionEngine(detectors, redactor=redactor)


_detector_option = click.option(
    "-d",
    "--detector",
    "detectors",
    multiple=True,
    metavar="NAME",
    help="Detector to enable (repeatable). Defaults to all when omitted.",
)
_mask_option = click.option(
    "--mask",
    is_flag=True,
    help="Mask matches with '*' instead of typed [REDACTED_*] placeholders.",
)
_keep_last_option = click.option(
    "--keep-last",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    help="When --mask is set, keep this many trailing characters visible.",
)
_encoding_option = click.option(
    "--encoding",
    default="utf-8",
    show_default=True,
    help="Text encoding used to read and write files.",
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, prog_name="redactai-engine")
def cli() -> None:
    """Stream text/log files and redact sensitive information (PII)."""


@cli.command(name="scrub")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@_detector_option
@_mask_option
@_keep_last_option
@_encoding_option
def scrub_command(
    input_path: Path,
    output_path: Path,
    detectors: tuple[str, ...],
    mask: bool,
    keep_last: int,
    encoding: str,
) -> None:
    """Scrub a single file: scrub INPUT OUTPUT."""
    engine = _build_engine(detectors, mask, keep_last)
    result = engine.scrub_file(input_path, output_path, encoding=encoding)
    if not result.ok:
        raise click.ClickException(f"Failed to scrub {input_path}: {result.error}")
    click.echo(f"Scrubbed {result.input_path} -> {result.output_path} ({result.matches} redactions)")


@cli.command(name="batch")
@click.argument(
    "input_paths",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory where scrubbed files are written.",
)
@click.option(
    "--suffix",
    default=".scrubbed",
    show_default=True,
    help="Suffix inserted before the file extension of each output file.",
)
@click.option(
    "-w",
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    help="Maximum worker threads (defaults to Python's ThreadPoolExecutor default).",
)
@_detector_option
@_mask_option
@_keep_last_option
@_encoding_option
def batch_command(
    input_paths: tuple[Path, ...],
    output_dir: Path,
    suffix: str,
    workers: int | None,
    detectors: tuple[str, ...],
    mask: bool,
    keep_last: int,
    encoding: str,
) -> None:
    """Scrub many files concurrently into OUTPUT_DIR using a thread pool."""
    engine = _build_engine(detectors, mask, keep_last)
    jobs: list[tuple[Path, Path]] = []
    for in_path in input_paths:
        out_name = f"{in_path.stem}{suffix}{in_path.suffix}"
        jobs.append((in_path, output_dir / out_name))

    results = engine.scrub_files(jobs, max_workers=workers, encoding=encoding)
    _report_batch(results)


def _report_batch(results: list[FileResult]) -> None:
    failures = [r for r in results if not r.ok]
    total_redactions = sum(r.matches for r in results if r.ok)
    for result in sorted(results, key=lambda r: str(r.input_path)):
        if result.ok:
            click.echo(f"  OK   {result.input_path} -> {result.output_path} ({result.matches})")
        else:
            click.echo(f"  FAIL {result.input_path}: {result.error}", err=True)
    click.echo(
        f"Processed {len(results)} file(s), {total_redactions} redaction(s), "
        f"{len(failures)} failure(s)."
    )
    if failures:
        raise SystemExit(1)


@cli.command(name="detectors")
def detectors_command() -> None:
    """List the available detectors."""
    for name in available_detectors():
        click.echo(name)


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover - thin wrapper
    """Entry point usable from ``python -m`` or tests."""
    cli.main(args=list(argv) if argv is not None else None)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
