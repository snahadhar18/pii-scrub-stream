"""Built-in detectors and a small registry for selecting them by name."""

from __future__ import annotations

from typing import Dict, List, Type

from redactai.engine.detectors.ai_detector import AIDetector
from redactai.engine.detectors.auth_tokens_detector import AuthTokensDetector
from redactai.engine.detectors.aws_detector import AWSAccessKeyDetector
from redactai.engine.detectors.base import Detector, Match, RegexDetector
from redactai.engine.detectors.cloud_keys_detector import CloudKeysDetector
from redactai.engine.detectors.credit_card_detector import CreditCardDetector
from redactai.engine.detectors.crypto_keys_detector import CryptoKeysDetector
from redactai.engine.detectors.email_detector import EmailDetector
from redactai.engine.detectors.generic_api_key_detector import GenericAPIKeyDetector
from redactai.engine.detectors.github_token_detector import GitHubTokenDetector
from redactai.engine.detectors.ip_detector import IPv4Detector, IPv6Detector
from redactai.engine.detectors.jwt_detector import JWTDetector
from redactai.engine.detectors.network_secrets_detector import NetworkSecretsDetector
from redactai.engine.detectors.openai_detector import OpenAIKeyDetector
from redactai.engine.detectors.password_detector import PasswordDetector
from redactai.engine.detectors.phone_detector import PhoneDetector
from redactai.engine.detectors.secret_detector import SecretDetector
from redactai.engine.detectors.ssn_detector import SSNDetector

#: Map of CLI-friendly names -> detector classes.
REGISTRY: dict[str, type[Detector]] = {
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
    "ai_entity": AIDetector,
    "github_token": GitHubTokenDetector,
    "password": PasswordDetector,
    "secret": SecretDetector,
    "cloud_keys": CloudKeysDetector,
    "auth_tokens": AuthTokensDetector,
    "crypto_keys": CryptoKeysDetector,
    "network_secrets": NetworkSecretsDetector,
}


def available_detectors() -> list[str]:
    """Return the sorted list of registered detector names."""
    return sorted(REGISTRY)


def build_detectors(names: list[str]) -> list[Detector]:
    """Instantiate detectors for the given ``names``.

    Raises:
        KeyError: if any name is not registered.
    """
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise KeyError(f"Unknown detector(s): {', '.join(unknown)}")
    detectors = []
    for name in names:
        try:
            detectors.append(REGISTRY[name]())
        except ImportError as e:
            raise ImportError(f"Cannot build detector '{name}': {e}") from e
    return detectors


def default_detectors() -> list[Detector]:
    """Instantiate one of every registered detector, skipping those with missing dependencies."""
    detectors = []
    for cls in REGISTRY.values():
        try:
            detectors.append(cls())
        except ImportError:
            pass
    return detectors


__all__ = [
    "Detector",
    "Match",
    "RegexDetector",
    "AIDetector",
    "AuthTokensDetector",
    "AWSAccessKeyDetector",
    "CloudKeysDetector",
    "CreditCardDetector",
    "CryptoKeysDetector",
    "EmailDetector",
    "GenericAPIKeyDetector",
    "GitHubTokenDetector",
    "IPv4Detector",
    "IPv6Detector",
    "JWTDetector",
    "NetworkSecretsDetector",
    "OpenAIKeyDetector",
    "PasswordDetector",
    "PhoneDetector",
    "SecretDetector",
    "SSNDetector",
    "REGISTRY",
    "available_detectors",
    "build_detectors",
    "default_detectors",
]
