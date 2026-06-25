"""Real-time stream processing from stdin (or any text stream).

Powers ``redactai stream`` for pipelines such as::

    tail -f app.log | redactai stream

Lines are read as they arrive, wrapped into :class:`Record` objects, and fed to
the :class:`ProcessingEngine`. Redacted output is written line-by-line to the
output stream so the tool behaves like a transparent filter. SIGINT/SIGTERM
trigger a graceful drain bounded by the configured grace period.
"""

from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Iterator
from typing import IO

from redactai.gateway.core.models import Record, ScanResult
from redactai.gateway.streaming.processor import ProcessingEngine

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Consume a live text stream and emit redacted lines in real time."""

    def __init__(
        self,
        engine: ProcessingEngine,
        *,
        source_name: str = "stdin",
        emit_redacted: bool = True,
        install_signal_handlers: bool = True,
    ) -> None:
        self.engine = engine
        self.source_name = source_name
        self.emit_redacted = emit_redacted
        self.install_signal_handlers = install_signal_handlers
        self._stop = threading.Event()

    def request_stop(self) -> None:
        """Ask the stream loop to finish the current line and drain."""
        self._stop.set()
        self.engine.request_stop()

    def _install_signals(self) -> None:
        if not self.install_signal_handlers:
            return

        def _handler(signum: int, _frame: object) -> None:
            logger.info("received signal %s; draining stream", signum)
            self.request_stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError):  # pragma: no cover - non-main thread/OS
                logger.debug("could not install handler for %s", sig)

    def _records(self, stream: IO[str]) -> Iterator[Record]:
        for line_no, raw in enumerate(stream, start=1):
            if self._stop.is_set():
                break
            content = raw.rstrip("\r\n")
            yield Record(
                id=f"{self.source_name}:{line_no}",
                content=content,
                source=self.source_name,
                offset=line_no,
                metadata={"line": line_no},
            )

    def run(self, stream: IO[str], output: IO[str]) -> int:
        """Process ``stream`` until EOF or stop; return the count of lines handled.

        The engine is started/stopped around the loop so worker threads are
        cleaned up deterministically even on Ctrl-C.
        """
        self._install_signals()
        processed = 0
        self.engine.start()
        try:
            for result in self.engine.process(self._records(stream)):
                self._write(result, output)
                processed += 1
                if self._stop.is_set():
                    break
        finally:
            self.engine.shutdown(wait=True)
            output.flush()
        logger.info("stream finished: %d lines processed", processed)
        return processed

    def _write(self, result: ScanResult, output: IO[str]) -> None:
        if self.emit_redacted:
            text = result.redacted if result.redacted is not None else ""
            output.write(text + "\n")
        else:
            labels = ",".join(result.labels)
            output.write(f"{result.record_id}\t{result.hit_count}\t{labels}\n")


__all__ = ["StreamProcessor"]
