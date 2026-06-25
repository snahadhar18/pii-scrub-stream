"""The concurrent processing engine.

:class:`ProcessingEngine` turns an iterable of :class:`Record` objects into a
stream of :class:`ScanResult` objects, executing detection across a
``ThreadPoolExecutor`` with the following production concerns handled:

* **Configurable workers** -- pool size from settings.
* **Batching** -- records are grouped so per-task overhead is amortized.
* **Backpressure** -- a bounded sliding window of in-flight batches stops a fast
  producer (e.g. a multi-GB file) from exhausting memory.
* **Fault tolerance** -- per-record retries with a fail-open fallback so one bad
  record never aborts the run.
* **Metrics** -- throughput, latency, processed records and queue depth.

Detection logic itself lives entirely in the injected :class:`ScanService`'s
detectors; the engine never inspects content.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from types import TracebackType

from redactai.gateway.core.models import Record, ScanResult, ScanSummary
from redactai.gateway.core.service import ScanService
from redactai.gateway.observability.metrics import MetricsRegistry
from redactai.gateway.observability.metrics import metrics as default_metrics

logger = logging.getLogger(__name__)


def _chunked(records: Iterable[Record], size: int) -> Iterator[list[Record]]:
    """Yield lists of up to ``size`` records from ``records``."""
    batch: list[Record] = []
    for record in records:
        batch.append(record)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


class ProcessingEngine:
    """Concurrent, backpressured record processor."""

    def __init__(
        self,
        scan_service: ScanService,
        *,
        workers: int = 4,
        batch_size: int = 256,
        queue_maxsize: int = 1000,
        max_retries: int = 2,
        redact: bool = True,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        if workers < 1:
            raise ValueError("workers must be >= 1")
        self.scan_service = scan_service
        self.workers = workers
        self.batch_size = max(1, batch_size)
        self.queue_maxsize = max(1, queue_maxsize)
        self.max_retries = max(0, max_retries)
        self.redact = redact
        self.metrics = metrics or default_metrics
        # Bound the number of in-flight *batches* to provide backpressure.
        self._max_inflight = max(workers, self.queue_maxsize // self.batch_size or 1)
        self._executor: ThreadPoolExecutor | None = None
        self._stop = threading.Event()

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        """Spin up the worker pool (idempotent)."""
        if self._executor is None:
            self._stop.clear()
            self._executor = ThreadPoolExecutor(
                max_workers=self.workers, thread_name_prefix="rg-worker"
            )

    def shutdown(self, *, wait: bool = True) -> None:
        """Tear down the worker pool."""
        self._stop.set()
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def request_stop(self) -> None:
        """Signal the engine to stop accepting new work (graceful shutdown)."""
        self._stop.set()

    def __enter__(self) -> ProcessingEngine:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.shutdown(wait=exc is None)

    # --- execution -------------------------------------------------------
    def process(self, records: Iterable[Record]) -> Iterator[ScanResult]:
        """Yield results for ``records`` in input order, with backpressure.

        A sliding window of at most ``_max_inflight`` batches is kept submitted
        to the pool. Results are yielded as the oldest batch completes while a
        replacement batch is submitted, keeping memory bounded irrespective of
        input size.
        """
        if self._executor is None:
            raise RuntimeError("engine not started; use `with engine:` or call start()")
        executor = self._executor
        batches = _chunked(records, self.batch_size)
        window: deque[Future[list[ScanResult]]] = deque()

        def submit_next() -> bool:
            if self._stop.is_set():
                return False
            try:
                batch = next(batches)
            except StopIteration:
                return False
            window.append(executor.submit(self._process_batch, batch))
            self.metrics.set_gauge("rg_queue_depth", len(window))
            return True

        for _ in range(self._max_inflight):
            if not submit_next():
                break

        while window:
            future = window.popleft()
            results = future.result()
            submit_next()
            self.metrics.set_gauge("rg_queue_depth", len(window))
            yield from results

    def run(self, records: Iterable[Record]) -> tuple[list[ScanResult], ScanSummary]:
        """Process everything eagerly and return results plus a summary.

        Convenience for batch CLI use where the full result set fits in memory.
        For large inputs prefer :meth:`process` and stream the results out.
        """
        started = time.perf_counter()
        results: list[ScanResult] = []
        spans = 0
        bytes_processed = 0
        label_counts: dict[str, int] = {}
        for result in self.process(records):
            results.append(result)
            spans += result.hit_count
            for span in result.spans:
                label_counts[span.label] = label_counts.get(span.label, 0) + 1
            if result.redacted is not None:
                bytes_processed += len(result.redacted.encode("utf-8"))
        duration_ms = (time.perf_counter() - started) * 1000.0
        summary = ScanSummary(
            records=len(results),
            spans=spans,
            bytes_processed=bytes_processed,
            duration_ms=duration_ms,
            errors=int(self.metrics.counter("rg_records_failed")),
            label_counts=label_counts,
        )
        return results, summary

    # --- internals -------------------------------------------------------
    def _process_batch(self, batch: list[Record]) -> list[ScanResult]:
        return [self._process_one(record) for record in batch]

    def _process_one(self, record: Record) -> ScanResult:
        attempt = 0
        while True:
            try:
                start = time.perf_counter()
                result = self.scan_service.scan(record, redact=self.redact)
                self.metrics.observe("rg_record_latency_ms", (time.perf_counter() - start) * 1000.0)
                self.metrics.increment("rg_records_processed")
                self.metrics.increment("rg_spans_detected", result.hit_count)
                return result
            except Exception:  # noqa: BLE001 - fault tolerance
                attempt += 1
                if attempt > self.max_retries:
                    self.metrics.increment("rg_records_failed")
                    logger.exception("record %s failed after %d attempts", record.id, attempt)
                    # Fail open: emit an empty result so the stream continues.
                    return ScanResult(record_id=record.id, source=record.source)
                self.metrics.increment("rg_records_retried")


__all__ = ["ProcessingEngine"]
