"""Broker and sink interface contracts for horizontal scaling.

These Protocols describe the minimal surface a transport must provide. Concrete
adapters (Redis Streams, Kafka, RabbitMQ) implement them in optional modules;
the core engine only ever depends on the Protocol, mirroring how detectors plug
in. An :class:`InMemoryBroker` is provided as a reference implementation for
tests and single-host deployments.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from redactai.gateway.core.models import Record, ScanResult


@dataclass(frozen=True)
class Message:
    """A unit of work on the wire.

    ``ack_token`` is opaque transport state used to acknowledge processing
    (e.g. a Redis stream id or a Kafka offset).
    """

    record: Record
    ack_token: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class MessageBroker(Protocol):
    """Transport for distributing records to a pool of remote workers."""

    def publish(self, record: Record) -> None:
        """Enqueue a record for processing by some consumer."""
        ...

    def consume(self, *, timeout: float | None = None) -> Iterator[Message]:
        """Yield messages as they arrive until the broker is closed."""
        ...

    def ack(self, message: Message) -> None:
        """Acknowledge that ``message`` was processed successfully."""
        ...

    def nack(self, message: Message) -> None:
        """Signal processing failure so the message can be retried/dead-lettered."""
        ...

    def close(self) -> None:
        """Release transport resources."""
        ...


@runtime_checkable
class ResultSink(Protocol):
    """Destination for completed :class:`ScanResult` objects."""

    def emit(self, result: ScanResult) -> None:
        """Publish a single result downstream."""
        ...

    def close(self) -> None:
        """Flush and release resources."""
        ...


class InMemoryBroker:
    """Thread-safe, single-process reference broker backed by ``queue.Queue``.

    Useful for tests and for running the distributed worker locally before a
    real transport is wired up. Acks are no-ops because delivery is in-process.
    """

    _SENTINEL = object()

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: queue.Queue[object] = queue.Queue(maxsize=maxsize)
        self._closed = threading.Event()

    def publish(self, record: Record) -> None:
        if self._closed.is_set():
            raise RuntimeError("broker is closed")
        self._queue.put(Message(record=record))

    def consume(self, *, timeout: float | None = None) -> Iterator[Message]:
        while not self._closed.is_set():
            try:
                item = self._queue.get(timeout=timeout if timeout is not None else 0.5)
            except queue.Empty:
                continue
            if item is self._SENTINEL:
                return
            assert isinstance(item, Message)
            yield item

    def ack(self, message: Message) -> None:  # noqa: D401 - in-process no-op
        """No-op: in-process delivery needs no acknowledgement."""

    def nack(self, message: Message) -> None:
        """Re-enqueue the message for another attempt."""
        if not self._closed.is_set():
            self._queue.put(message)

    def close(self) -> None:
        self._closed.set()
        self._queue.put(self._SENTINEL)


__all__ = ["Message", "MessageBroker", "ResultSink", "InMemoryBroker"]
