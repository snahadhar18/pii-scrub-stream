"""US Social Security Number detector."""

from __future__ import annotations

import re

from pii_scrub_stream.detectors.base import RegexDetector

_SSN_RE = re.compile(r"\b(?!000|666|9\d\d)\d{3}[ \-]?(?!00)\d{2}[ \-]?(?!0000)\d{4}\b")


class SSNDetector(RegexDetector):
    """Detect US SSNs such as ``123-45-6789`` (excludes known invalid ranges)."""

    label = "SSN"
    pattern = _SSN_RE
