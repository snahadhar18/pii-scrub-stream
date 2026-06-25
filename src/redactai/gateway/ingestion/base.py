"""The ingestion source abstraction.

:class:`BaseIngestionSource` defines the contract every concrete source obeys.
It is both a context manager (so file handles are deterministically closed) and
an iterable of :class:`Record`. An async iterator is provided for free by
offloading the blocking, chunked reads onto a worker thread, which lets the
FastAPI layer ingest large files without blocking the event loop.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from types import TracebackType

from redactai.gateway.core.models import Record


class BaseIngestionSource(ABC):
    """Abstract, memory-efficient producer of :class:`Record` objects.

    Subclasses implement :meth:`open`, :meth:`close` and :meth:`read_records`.
    Consumers should prefer the context-manager / iterator protocols::

        with FileSource(path) as src:
            for record in src:
                ...
    """

    #: Logical source identifier surfaced on every emitted record.
    source_name: str = "source"

    # --- lifecycle -------------------------------------------------------
    def open(self) -> None:
        """Acquire any underlying resources (override as needed)."""

    def close(self) -> None:
        """Release any underlying resources (override as needed)."""

    def __enter__(self) -> BaseIngestionSource:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    async def __aenter__(self) -> BaseIngestionSource:
        await asyncio.to_thread(self.open)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await asyncio.to_thread(self.close)

    # --- production ------------------------------------------------------
    @abstractmethod
    def read_records(self) -> Iterator[Record]:
        """Yield records lazily. Must not load the whole input into memory."""
        raise NotImplementedError

    def __iter__(self) -> Iterator[Record]:
        return self.read_records()

    async def aiter_records(self, chunk: int = 256) -> AsyncIterator[Record]:
        """Async view over :meth:`read_records`.

        The synchronous generator is drained in ``chunk``-sized batches on a
        worker thread so the event loop is never blocked on disk I/O.
        """
        iterator = self.read_records()
        loop = asyncio.get_running_loop()

        def _next_batch() -> list[Record]:
            batch: list[Record] = []
            for _ in range(chunk):
                try:
                    batch.append(next(iterator))
                except StopIteration:
                    break
            return batch

        while True:
            batch = await loop.run_in_executor(None, _next_batch)
            if not batch:
                return
            for record in batch:
                yield record


__all__ = ["BaseIngestionSource"]
