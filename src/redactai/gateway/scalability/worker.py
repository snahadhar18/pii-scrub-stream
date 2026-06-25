"""Distributed worker -- consume from a broker, scan, publish results.

:class:`DistributedWorker` is the horizontal-scaling unit: run N of them across
M hosts, all pulling from the same :class:`MessageBroker`. Each worker reuses the
in-process :class:`ProcessingEngine` for intra-worker concurrency, giving two
levels of parallelism (processes x threads). The worker is transport-agnostic --
swap the broker for Redis/Kafka/RabbitMQ with no code change here.
"""

from __future__ import annotations

import logging
import threading

from redactai.gateway.scalability.broker import MessageBroker, ResultSink
from redactai.gateway.streaming.processor import ProcessingEngine

logger = logging.getLogger(__name__)


class DistributedWorker:
    """Pulls records from a broker, scans them, and emits results to a sink."""

    def __init__(
        self,
        broker: MessageBroker,
        engine: ProcessingEngine,
        sink: ResultSink | None = None,
        *,
        poll_timeout: float = 0.5,
    ) -> None:
        self.broker = broker
        self.engine = engine
        self.sink = sink
        self.poll_timeout = poll_timeout
        self._stop = threading.Event()

    def request_stop(self) -> None:
        """Ask the worker loop to finish the current message and exit."""
        self._stop.set()

    def run(self) -> int:
        """Consume until the broker closes or a stop is requested.

        Returns the number of messages processed. Each message is processed with
        the engine's per-record fault tolerance; on an unexpected failure the
        message is nacked for redelivery.
        """
        processed = 0
        self.engine.start()
        try:
            for message in self.broker.consume(timeout=self.poll_timeout):
                if self._stop.is_set():
                    self.broker.nack(message)
                    break
                try:
                    result = self.engine.scan_service.scan(
                        message.record, redact=self.engine.redact
                    )
                    if self.sink is not None:
                        self.sink.emit(result)
                    self.broker.ack(message)
                    processed += 1
                except Exception:  # noqa: BLE001
                    logger.exception("worker failed on %s; nacking", message.record.id)
                    self.broker.nack(message)
        finally:
            self.engine.shutdown(wait=True)
        return processed


__all__ = ["DistributedWorker"]
