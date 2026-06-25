"""Built-in detectors and a small registry for selecting them by name."""

from __future__ import annotations

from typing import Dict, List, Type

from pii_scrub_stream.detectors.base import Detector, Match, RegexDetector
from pii_scrub_stream.detectors.credit_card import CreditCardDetector
from pii_scrub_stream.detectors.email import EmailDetector
from pii_scrub_stream.detectors.ip import IPv4Detector, IPv6Detector
from pii_scrub_stream.detectors.phone import PhoneDetector
from pii_scrub_stream.detectors.ssn import SSNDetector

#: Map of CLI-friendly names -> detector classes.
REGISTRY: Dict[str, Type[Detector]] = {
    "email": EmailDetector,
    "phone": PhoneDetector,
    "ipv4": IPv4Detector,
    "ipv6": IPv6Detector,
    "credit_card": CreditCardDetector,
    "ssn": SSNDetector,
}


def available_detectors() -> List[str]:
    """Return the sorted list of registered detector names."""
    return sorted(REGISTRY)


def build_detectors(names: List[str]) -> List[Detector]:
    """Instantiate detectors for the given ``names``.

    Raises:
        KeyError: if any name is not registered.
    """
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise KeyError(f"Unknown detector(s): {', '.join(unknown)}")
    return [REGISTRY[name]() for name in names]


def default_detectors() -> List[Detector]:
    """Instantiate one of every registered detector."""
    return [cls() for cls in REGISTRY.values()]


__all__ = [
    "Detector",
    "Match",
    "RegexDetector",
    "CreditCardDetector",
    "EmailDetector",
    "IPv4Detector",
    "IPv6Detector",
    "PhoneDetector",
    "SSNDetector",
    "REGISTRY",
    "available_detectors",
    "build_detectors",
    "default_detectors",
]
