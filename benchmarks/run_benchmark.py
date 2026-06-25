"""Throughput / latency benchmark for the concurrent processing engine.

This measures *infrastructure* performance (fan-out, batching, backpressure)
independent of any real detector. A :class:`SyntheticDetector` simulates a
configurable per-record CPU cost so we can characterize how the engine scales
with worker count and batch size without coupling the benchmark to detection
logic.

Run::

    python -m benchmarks.run_benchmark --records 100000 --workers 8 --work-us 50
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence

from redactai.gateway.core.detector import DetectionSpan, Detector
from redactai.gateway.core.models import Record
from redactai.gateway.core.service import ScanService
from redactai.gateway.streaming.processor import ProcessingEngine


class SyntheticDetector(Detector):
    """A benchmark fixture that burns a fixed amount of CPU per call.

    Not a real detector: it performs deterministic busy-work to model detector
    cost so the engine's overhead and scaling can be measured in isolation.
    """

    name = "synthetic"

    def __init__(self, work_us: float = 0.0) -> None:
        self.work_us = work_us

    def detect(self, text: str) -> Sequence[DetectionSpan]:
        if self.work_us > 0:
            deadline = time.perf_counter() + self.work_us / 1_000_000
            x = 0
            while time.perf_counter() < deadline:
                x += 1  # noqa: F841 - intentional busy-work
        return ()


def _records(n: int) -> list[Record]:
    line = "user john.doe@example.com logged in from 10.0.0.1 with card 4111111111111111"
    return [Record(id=str(i), content=line, source="bench") for i in range(n)]


def run(records: int, workers: int, batch_size: int, work_us: float) -> dict[str, float]:
    """Run one benchmark configuration and return measured metrics."""
    service = ScanService([SyntheticDetector(work_us)])
    data = _records(records)
    start = time.perf_counter()
    with ProcessingEngine(service, workers=workers, batch_size=batch_size, redact=True) as engine:
        count = sum(1 for _ in engine.process(data))
    elapsed = time.perf_counter() - start
    return {
        "records": count,
        "workers": workers,
        "batch_size": batch_size,
        "work_us": work_us,
        "elapsed_s": round(elapsed, 4),
        "throughput_rps": round(count / elapsed, 1) if elapsed else 0.0,
        "latency_ms_per_record": round(elapsed / count * 1000, 4) if count else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RedactAI engine benchmark")
    parser.add_argument("--records", type=int, default=50_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument(
        "--work-us", type=float, default=10.0, help="Simulated per-record CPU cost (us)."
    )
    parser.add_argument("--sweep", action="store_true", help="Sweep worker counts 1,2,4,8.")
    args = parser.parse_args(argv)

    if args.sweep:
        print(f"{'workers':>8} {'rps':>12} {'elapsed_s':>10}")
        for w in (1, 2, 4, 8):
            r = run(args.records, w, args.batch_size, args.work_us)
            print(f"{w:>8} {r['throughput_rps']:>12} {r['elapsed_s']:>10}")
    else:
        result = run(args.records, args.workers, args.batch_size, args.work_us)
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
