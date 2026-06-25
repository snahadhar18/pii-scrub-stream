"""In-process, thread-safe metrics collection.

A deliberately tiny metrics facade: counters, gauges and histograms guarded by a
single lock. It exposes a Prometheus-style text snapshot for the ``/metrics``
endpoint and a JSON snapshot for programmatic use. The design lets us avoid a
hard dependency on ``prometheus_client`` while remaining compatible with it --
the scalability roadmap (Milestone 9) describes swapping this for a real
multiprocess collector.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class _Histogram:
    """Fixed-bucket histogram tracking count, sum and quantile-able buckets."""

    buckets: tuple[float, ...] = (1, 5, 10, 25, 50, 100, 250, 500, 1000, math.inf)
    counts: list[int] = field(default_factory=list)
    total: float = 0.0
    n: int = 0

    def __post_init__(self) -> None:
        if not self.counts:
            self.counts = [0] * len(self.buckets)

    def observe(self, value: float) -> None:
        self.total += value
        self.n += 1
        for i, edge in enumerate(self.buckets):
            if value <= edge:
                self.counts[i] += 1
                break

    @property
    def mean(self) -> float:
        return self.total / self.n if self.n else 0.0


class MetricsRegistry:
    """Thread-safe registry of counters, gauges and histograms."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, _Histogram] = {}
        self._created = time.time()

    def increment(self, name: str, value: float = 1.0) -> None:
        """Add ``value`` to a monotonically increasing counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set an instantaneous gauge value (e.g. current queue depth)."""
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        """Record an observation (e.g. latency in ms) into a histogram."""
        with self._lock:
            hist = self._histograms.get(name)
            if hist is None:
                hist = self._histograms[name] = _Histogram()
            hist.observe(value)

    def counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0.0)

    def gauge(self, name: str) -> float:
        with self._lock:
            return self._gauges.get(name, 0.0)

    def snapshot(self) -> Mapping[str, object]:
        """Return a JSON-serializable view of all metrics."""
        with self._lock:
            uptime = time.time() - self._created
            return {
                "uptime_seconds": uptime,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: {"count": h.n, "sum": h.total, "mean": h.mean}
                    for name, h in self._histograms.items()
                },
            }

    def render_prometheus(self) -> str:
        """Render metrics in the Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            for name, value in sorted(self._counters.items()):
                metric = _safe(name)
                lines.append(f"# TYPE {metric} counter")
                lines.append(f"{metric} {value}")
            for name, value in sorted(self._gauges.items()):
                metric = _safe(name)
                lines.append(f"# TYPE {metric} gauge")
                lines.append(f"{metric} {value}")
            for name, hist in sorted(self._histograms.items()):
                metric = _safe(name)
                lines.append(f"# TYPE {metric} summary")
                lines.append(f"{metric}_count {hist.n}")
                lines.append(f"{metric}_sum {hist.total}")
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Clear all metrics (primarily for tests)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._created = time.time()


def _safe(name: str) -> str:
    """Coerce a metric name into a valid Prometheus identifier."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


class Timer:
    """Context manager that records elapsed milliseconds into a histogram."""

    def __init__(self, registry: MetricsRegistry, name: str) -> None:
        self._registry = registry
        self._name = name
        self._start = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        self._registry.observe(self._name, elapsed_ms)


#: Process-wide default registry used by the engine and API.
metrics = MetricsRegistry()


__all__ = ["MetricsRegistry", "Timer", "metrics"]
