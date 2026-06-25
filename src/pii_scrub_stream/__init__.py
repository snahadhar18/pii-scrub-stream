"""pii-scrub-stream: stream text/log files and redact sensitive information."""

from pii_scrub_stream.detectors.base import Detector, Match, RegexDetector
from pii_scrub_stream.scrubber.engine import RedactionEngine

__all__ = ["Detector", "Match", "RegexDetector", "RedactionEngine", "__version__"]
__version__ = "0.1.0"
