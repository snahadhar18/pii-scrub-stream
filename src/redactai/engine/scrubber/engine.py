"""The redaction engine: orchestrates detectors and rewrites text safely.

Design goals:
  * Composable - accepts any number of detectors.
  * Streaming - process files line-by-line so arbitrarily large logs fit in
    constant memory.
  * Concurrent - process many files in parallel with a thread pool (work is
    largely I/O bound: read -> scrub -> write).
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Union

from redactai.engine.detectors.base import Detector, Match
from redactai.engine.scrubber.redaction import Redactor, label_redactor

PathLike = Union[str, "os.PathLike[str]"]


@dataclass
class FileResult:
    """Outcome of scrubbing a single file."""

    input_path: Path
    output_path: Path
    matches: int
    ok: bool
    error: str | None = None


def resolve_overlaps(matches: list[Match]) -> list[Match]:
    """Return a non-overlapping, ordered subset of ``matches``.

    When spans overlap, prefer the one that starts earliest; ties are broken
    in favour of the longer span. This keeps redaction deterministic even
    when multiple detectors fire on the same region.
    """
    if not matches:
        return []
    ordered = sorted(matches, key=lambda m: (m.start, -m.length))
    chosen: list[Match] = []
    cursor = -1
    for match in ordered:
        if match.start >= cursor:
            chosen.append(match)
            cursor = match.end
    return chosen


class RedactionEngine:
    """Run a set of detectors over text/files and replace sensitive spans."""

    def __init__(
        self,
        detectors: Sequence[Detector],
        redactor: Redactor | None = None,
    ) -> None:
        if not detectors:
            raise ValueError("RedactionEngine requires at least one detector")
        self.detectors: list[Detector] = list(detectors)
        self.redactor: Redactor = redactor or label_redactor

    # -- core text API -----------------------------------------------------

    def find_matches(self, text: str) -> list[Match]:
        """Collect, then de-overlap, matches from every detector."""
        found: list[Match] = []
        for detector in self.detectors:
            found.extend(detector.detect(text))
        return resolve_overlaps(found)

    def scrub_text(self, text: str) -> tuple[str, int]:
        """Return ``(redacted_text, match_count)`` for a single chunk of text."""
        matches = self.find_matches(text)
        if not matches:
            return text, 0
        pieces: list[str] = []
        cursor = 0
        for match in matches:
            pieces.append(text[cursor : match.start])
            pieces.append(self.redactor(match))
            cursor = match.end
        pieces.append(text[cursor:])
        return "".join(pieces), len(matches)

    # -- streaming API -----------------------------------------------------

    def scrub_stream(self, source: Iterable[str], sink: IO[str]) -> int:
        """Scrub an iterable of lines, writing results to ``sink``.

        Returns the total number of redactions performed. Processing is
        line-oriented, which bounds memory use regardless of file size.
        """
        total = 0
        for line in source:
            redacted, count = self.scrub_text(line)
            sink.write(redacted)
            total += count
        return total

    def scrub_file(
        self,
        input_path: PathLike,
        output_path: PathLike,
        encoding: str = "utf-8",
    ) -> FileResult:
        """Scrub ``input_path`` and write the result to ``output_path``."""
        in_path = Path(input_path)
        out_path = Path(output_path)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with (
                in_path.open("r", encoding=encoding, errors="replace") as src,
                out_path.open("w", encoding=encoding, newline="") as dst,
            ):
                total = self.scrub_stream(src, dst)
            return FileResult(in_path, out_path, total, ok=True)
        except OSError as exc:
            return FileResult(in_path, out_path, 0, ok=False, error=str(exc))

    # -- concurrent API ----------------------------------------------------

    def scrub_files(
        self,
        jobs: Iterable[tuple[PathLike, PathLike]],
        max_workers: int | None = None,
        encoding: str = "utf-8",
    ) -> list[FileResult]:
        """Scrub many ``(input, output)`` pairs concurrently.

        Uses a :class:`~concurrent.futures.ThreadPoolExecutor` since the work
        is I/O bound. Returns a :class:`FileResult` for each job; failures are
        captured per-file rather than aborting the whole batch.
        """
        job_list = list(jobs)
        if not job_list:
            return []
        results: list[FileResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self.scrub_file, src, dst, encoding): (src, dst)
                for src, dst in job_list
            }
            for future in as_completed(futures):
                results.append(future.result())
        return results
