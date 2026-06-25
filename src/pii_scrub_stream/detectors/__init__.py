"""Built-in detectors and a small registry for selecting them by name."""

from __future__ import annotations

from typing import Dict, List, Type

from pii_scrub_stream.detectors.base import Detector, Match, RegexDetector
from pii_scrub_stream.detectors.aws_key import AWSAccessKeyDetector
from pii_scrub_stream.detectors.credit_card import CreditCardDetector
from pii_scrub_stream.detectors.email import EmailDetector
from pii_scrub_stream.detectors.generic_api_key import GenericAPIKeyDetector
from pii_scrub_stream.detectors.ip import IPv4Detector, IPv6Detector
from pii_scrub_stream.detectors.jwt import JWTDetector
from pii_scrub_stream.detectors.openai_key import OpenAIKeyDetector
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
    "jwt": JWTDetector,
    "aws_key": AWSAccessKeyDetector,
    "openai_key": OpenAIKeyDetector,
    "generic_api_key": GenericAPIKeyDetector,
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
    "AWSAccessKeyDetector",
    "CreditCardDetector",
    "EmailDetector",
    "GenericAPIKeyDetector",
    "IPv4Detector",
    "IPv6Detector",
    "JWTDetector",
    "OpenAIKeyDetector",
    "PhoneDetector",
    "SSNDetector",
    "REGISTRY",
    "available_detectors",
    "build_detectors",
    "default_detectors",
]
