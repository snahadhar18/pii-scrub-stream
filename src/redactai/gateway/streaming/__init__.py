"""Processing engine and real-time streaming.

This package owns *execution*: how records are fanned out across worker threads
(:class:`ProcessingEngine`) and how a live stdin stream is consumed in real time
with graceful shutdown (:class:`StreamProcessor`).
"""

from __future__ import annotations

from redactai.gateway.streaming.processor import ProcessingEngine
from redactai.gateway.streaming.stream import StreamProcessor

__all__ = ["ProcessingEngine", "StreamProcessor"]
