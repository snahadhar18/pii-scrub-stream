"""IP address detectors (IPv4 and IPv6)."""

from __future__ import annotations

import re

from pii_scrub_stream.detectors.base import RegexDetector

_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_IPV4_RE = re.compile(rf"\b(?:{_OCTET}\.){{3}}{_OCTET}\b")

# Pragmatic IPv6 matcher (covers full and "::"-compressed forms).
_IPV6_RE = re.compile(
    r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"
    r"|\b(?:[A-Fa-f0-9]{1,4}:){1,7}:\b"
    r"|\b::(?:[A-Fa-f0-9]{1,4}:){0,6}[A-Fa-f0-9]{1,4}\b",
)


class IPv4Detector(RegexDetector):
    """Detect IPv4 addresses such as ``192.168.0.1``."""

    label = "IPV4"
    pattern = _IPV4_RE


class IPv6Detector(RegexDetector):
    """Detect IPv6 addresses such as ``2001:db8::1``."""

    label = "IPV6"
    pattern = _IPV6_RE
