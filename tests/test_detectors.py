"""Comprehensive unit tests for all detectors.

Tests cover:
- Email addresses
- Phone numbers
- Credit card numbers (with Luhn validation)
- IP addresses (IPv4 and IPv6)
- US SSNs
- JWT tokens
- AWS Access Keys
- OpenAI API keys
- Generic API keys

Each detector test verifies:
1. Positive detection (true positives)
2. Negative detection (true negatives)
3. Confidence scoring
4. Replacement tag generation
5. Match location accuracy
"""

from __future__ import annotations

import base64
import json

import pytest

from pii_scrub_stream.detectors import (
    REGISTRY,
    available_detectors,
    build_detectors,
    default_detectors,
)
from pii_scrub_stream.detectors.aws_key import AWSAccessKeyDetector
from pii_scrub_stream.detectors.credit_card import CreditCardDetector, luhn_checksum_valid
from pii_scrub_stream.detectors.email import EmailDetector
from pii_scrub_stream.detectors.generic_api_key import GenericAPIKeyDetector, _shannon_entropy
from pii_scrub_stream.detectors.ip import IPv4Detector, IPv6Detector
from pii_scrub_stream.detectors.jwt import JWTDetector
from pii_scrub_stream.detectors.openai_key import OpenAIKeyDetector
from pii_scrub_stream.detectors.phone import PhoneDetector
from pii_scrub_stream.detectors.ssn import SSNDetector


def _values(detector, text):
    """Extract matched values from a detector run."""
    return [m.value for m in detector.detect(text)]


def _first_match(detector, text):
    """Return the first match or None."""
    matches = detector.detect(text)
    return matches[0] if matches else None


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailDetector:
    """Tests for EmailDetector."""

    def test_basic_email_detection(self):
        det = EmailDetector()
        found = _values(det, "Contact alice@example.com or bob.smith+tag@sub.domain.io please.")
        assert "alice@example.com" in found
        assert "bob.smith+tag@sub.domain.io" in found

    def test_email_labels_and_location(self):
        det = EmailDetector()
        matches = det.detect("x@y.com")
        assert matches and matches[0].label == "EMAIL"
        assert matches[0].value == "x@y.com"
        assert (matches[0].start, matches[0].end) == (0, 7)

    def test_email_confidence(self):
        det = EmailDetector()
        m = _first_match(det, "john@gmail.com")
        assert m is not None
        assert m.confidence == 0.99

    def test_email_replacement_tag(self):
        det = EmailDetector()
        m = _first_match(det, "john@gmail.com")
        assert m is not None
        assert m.replacement == "[EMAIL_REDACTED]"

    def test_email_output_format(self):
        """Verify the to_dict() output matches the required format."""
        det = EmailDetector()
        m = _first_match(det, "john@gmail.com")
        assert m is not None
        d = m.to_dict()
        assert d == {
            "match": "john@gmail.com",
            "type": "EMAIL",
            "start": 0,
            "end": 14,
            "confidence": 0.99,
            "replacement": "[EMAIL_REDACTED]",
        }

    def test_multiple_emails_in_text(self):
        det = EmailDetector()
        text = "send to a@b.com cc c@d.com bcc e@f.org"
        found = _values(det, text)
        assert len(found) == 3
        assert "a@b.com" in found
        assert "c@d.com" in found
        assert "e@f.org" in found

    def test_email_with_underscores_and_numbers(self):
        det = EmailDetector()
        found = _values(det, "user_123@company-name.co.uk")
        assert "user_123@company-name.co.uk" in found

    def test_no_false_positive_on_at_sign(self):
        det = EmailDetector()
        assert _values(det, "meet me @ the park") == []

    def test_no_false_positive_on_twitter_handle(self):
        det = EmailDetector()
        assert _values(det, "@username on twitter") == []


# ═══════════════════════════════════════════════════════════════════════════
# PHONE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestPhoneDetector:
    """Tests for PhoneDetector."""

    @pytest.mark.parametrize(
        "text",
        [
            "Call +1 (555) 123-4567 now",
            "phone: 555-123-4567",
            "tel 555.123.4567",
        ],
    )
    def test_phone_detection(self, text):
        det = PhoneDetector()
        assert _values(det, text), f"expected a phone match in {text!r}"

    def test_phone_ignores_short_numbers(self):
        det = PhoneDetector()
        assert _values(det, "order 12345 shipped") == []

    def test_phone_with_country_code_higher_confidence(self):
        det = PhoneDetector()
        m = _first_match(det, "+1 (555) 123-4567")
        assert m is not None
        assert m.confidence >= 0.90

    def test_phone_with_parens_higher_confidence(self):
        det = PhoneDetector()
        m = _first_match(det, "(555) 123-4567")
        assert m is not None
        assert m.confidence >= 0.90

    def test_phone_replacement_tag(self):
        det = PhoneDetector()
        m = _first_match(det, "555-123-4567")
        assert m is not None
        assert m.replacement == "[PHONE_REDACTED]"

    def test_phone_label(self):
        det = PhoneDetector()
        m = _first_match(det, "555-123-4567")
        assert m is not None
        assert m.label == "PHONE"

    def test_phone_rejects_too_many_digits(self):
        det = PhoneDetector()
        # 16+ digits should not match as a phone number
        assert _values(det, "1234567890123456") == []


# ═══════════════════════════════════════════════════════════════════════════
# CREDIT CARD DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestCreditCardDetector:
    """Tests for CreditCardDetector."""

    def test_luhn_valid_visa(self):
        det = CreditCardDetector()
        assert _values(det, "card 4111 1111 1111 1111") == ["4111 1111 1111 1111"]

    def test_luhn_rejects_invalid(self):
        det = CreditCardDetector()
        assert _values(det, "card 1234 5678 9012 3456") == []

    def test_luhn_helper(self):
        assert luhn_checksum_valid("4111111111111111")
        assert not luhn_checksum_valid("4111111111111112")
        assert not luhn_checksum_valid("123")

    def test_visa_high_confidence(self):
        det = CreditCardDetector()
        m = _first_match(det, "4111111111111111")
        assert m is not None
        assert m.confidence == 0.99  # Visa prefix

    def test_mastercard_high_confidence(self):
        det = CreditCardDetector()
        # Mastercard test number (Luhn-valid)
        m = _first_match(det, "5500000000000004")
        assert m is not None
        assert m.confidence == 0.99

    def test_amex_high_confidence(self):
        det = CreditCardDetector()
        # Amex test number (Luhn-valid, 15 digits)
        m = _first_match(det, "378282246310005")
        assert m is not None
        assert m.confidence == 0.99

    def test_credit_card_replacement_tag(self):
        det = CreditCardDetector()
        m = _first_match(det, "4111111111111111")
        assert m is not None
        assert m.replacement == "[CREDIT_CARD_REDACTED]"

    def test_credit_card_with_hyphens(self):
        det = CreditCardDetector()
        found = _values(det, "4111-1111-1111-1111")
        assert len(found) == 1

    def test_credit_card_with_spaces(self):
        det = CreditCardDetector()
        found = _values(det, "4111 1111 1111 1111")
        assert len(found) == 1

    def test_credit_card_label(self):
        det = CreditCardDetector()
        m = _first_match(det, "4111111111111111")
        assert m is not None
        assert m.label == "CREDIT_CARD"


# ═══════════════════════════════════════════════════════════════════════════
# IP ADDRESS DETECTORS
# ═══════════════════════════════════════════════════════════════════════════


class TestIPv4Detector:
    """Tests for IPv4Detector."""

    def test_ipv4_detection(self):
        det = IPv4Detector()
        found = _values(det, "src=192.168.0.1 dst=255.255.255.255 bad=999.1.1.1")
        assert "192.168.0.1" in found
        assert "255.255.255.255" in found
        assert "999.1.1.1" not in found

    def test_ipv4_confidence(self):
        det = IPv4Detector()
        m = _first_match(det, "192.168.1.1")
        assert m is not None
        assert m.confidence == 0.95

    def test_ipv4_replacement_tag(self):
        det = IPv4Detector()
        m = _first_match(det, "10.0.0.1")
        assert m is not None
        assert m.replacement == "[IPV4_REDACTED]"

    def test_ipv4_rejects_out_of_range(self):
        det = IPv4Detector()
        assert _values(det, "300.1.1.1") == []
        assert _values(det, "1.256.1.1") == []


class TestIPv6Detector:
    """Tests for IPv6Detector."""

    def test_ipv6_detection(self):
        det = IPv6Detector()
        found = _values(det, "addr 2001:db8::1 here")
        assert any("2001:db8" in v for v in found)

    def test_ipv6_confidence(self):
        det = IPv6Detector()
        m = _first_match(det, "2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert m is not None
        assert m.confidence == 0.90

    def test_ipv6_replacement_tag(self):
        det = IPv6Detector()
        m = _first_match(det, "2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert m is not None
        assert m.replacement == "[IPV6_REDACTED]"


# ═══════════════════════════════════════════════════════════════════════════
# SSN DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestSSNDetector:
    """Tests for SSNDetector."""

    def test_ssn_detection(self):
        det = SSNDetector()
        found = _values(det, "ssn 123-45-6789 and 078-05-1120")
        assert "123-45-6789" in found

    def test_ssn_rejects_invalid_area(self):
        det = SSNDetector()
        assert _values(det, "000-12-3456") == []

    def test_ssn_dashed_higher_confidence(self):
        det = SSNDetector()
        m = _first_match(det, "123-45-6789")
        assert m is not None
        assert m.confidence == 0.95

    def test_ssn_replacement_tag(self):
        det = SSNDetector()
        m = _first_match(det, "123-45-6789")
        assert m is not None
        assert m.replacement == "[SSN_REDACTED]"

    def test_ssn_label(self):
        det = SSNDetector()
        m = _first_match(det, "123-45-6789")
        assert m is not None
        assert m.label == "SSN"


# ═══════════════════════════════════════════════════════════════════════════
# JWT DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


def _make_jwt(
    header: dict | None = None,
    payload: dict | None = None,
    signature: str = "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
) -> str:
    """Helper to build a realistic JWT string."""
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}
    if payload is None:
        payload = {"sub": "1234567890", "name": "John Doe", "iat": 1516239022}
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{h}.{p}.{signature}"


class TestJWTDetector:
    """Tests for JWTDetector."""

    def test_jwt_detection_valid_header(self):
        det = JWTDetector()
        token = _make_jwt()
        matches = det.detect(f"Authorization: Bearer {token}")
        assert len(matches) == 1
        assert matches[0].value == token

    def test_jwt_high_confidence_with_valid_header(self):
        det = JWTDetector()
        token = _make_jwt()
        m = _first_match(det, token)
        assert m is not None
        assert m.confidence == 0.99  # Valid header decodes to JSON with 'alg'

    def test_jwt_label(self):
        det = JWTDetector()
        token = _make_jwt()
        m = _first_match(det, token)
        assert m is not None
        assert m.label == "JWT"

    def test_jwt_replacement_tag(self):
        det = JWTDetector()
        token = _make_jwt()
        m = _first_match(det, token)
        assert m is not None
        assert m.replacement == "[JWT_REDACTED]"

    def test_jwt_output_format(self):
        det = JWTDetector()
        token = _make_jwt()
        m = _first_match(det, f"token={token}")
        assert m is not None
        d = m.to_dict()
        assert d["type"] == "JWT"
        assert d["confidence"] == 0.99
        assert d["replacement"] == "[JWT_REDACTED]"
        assert d["match"] == token

    def test_jwt_no_false_positive_on_dotted_words(self):
        det = JWTDetector()
        assert _values(det, "file.name.ext") == []
        assert _values(det, "www.example.com") == []

    def test_jwt_multiple_tokens(self):
        det = JWTDetector()
        t1 = _make_jwt()
        t2 = _make_jwt(payload={"sub": "other", "iat": 9999999})
        text = f"token1={t1} and token2={t2}"
        matches = det.detect(text)
        assert len(matches) == 2

    def test_jwt_location_accuracy(self):
        det = JWTDetector()
        token = _make_jwt()
        prefix = "Bearer "
        text = prefix + token
        m = _first_match(det, text)
        assert m is not None
        assert m.start == len(prefix)
        assert m.end == len(text)
        assert text[m.start : m.end] == token


# ═══════════════════════════════════════════════════════════════════════════
# AWS ACCESS KEY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestAWSAccessKeyDetector:
    """Tests for AWSAccessKeyDetector."""

    def test_akia_detection(self):
        det = AWSAccessKeyDetector()
        text = "aws_access_key_id = AKIAIOSFODNN7EXAMPLE"
        found = _values(det, text)
        assert "AKIAIOSFODNN7EXAMPLE" in found

    def test_asia_detection(self):
        det = AWSAccessKeyDetector()
        text = "key: ASIAIOSFODNN7EXAMPLA"
        found = _values(det, text)
        assert "ASIAIOSFODNN7EXAMPLA" in found

    def test_akia_high_confidence(self):
        det = AWSAccessKeyDetector()
        m = _first_match(det, "AKIAIOSFODNN7EXAMPLE")
        assert m is not None
        assert m.confidence == 0.99

    def test_aws_key_label(self):
        det = AWSAccessKeyDetector()
        m = _first_match(det, "AKIAIOSFODNN7EXAMPLE")
        assert m is not None
        assert m.label == "AWS_KEY"

    def test_aws_key_replacement_tag(self):
        det = AWSAccessKeyDetector()
        m = _first_match(det, "AKIAIOSFODNN7EXAMPLE")
        assert m is not None
        assert m.replacement == "[AWS_KEY_REDACTED]"

    def test_aws_secret_key_detection(self):
        det = AWSAccessKeyDetector()
        text = "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        matches = det.detect(text)
        secret_matches = [m for m in matches if m.label == "AWS_SECRET"]
        assert len(secret_matches) == 1
        assert secret_matches[0].value == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_aws_secret_replacement_tag(self):
        det = AWSAccessKeyDetector()
        text = "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        matches = det.detect(text)
        secret_matches = [m for m in matches if m.label == "AWS_SECRET"]
        assert len(secret_matches) == 1
        assert secret_matches[0].replacement == "[AWS_SECRET_REDACTED]"

    def test_aws_key_output_format(self):
        det = AWSAccessKeyDetector()
        m = _first_match(det, "AKIAIOSFODNN7EXAMPLE")
        assert m is not None
        d = m.to_dict()
        assert d["type"] == "AWS_KEY"
        assert d["confidence"] == 0.99
        assert d["replacement"] == "[AWS_KEY_REDACTED]"

    def test_no_false_positive_on_random_uppercase(self):
        det = AWSAccessKeyDetector()
        # 20 chars but wrong prefix
        assert _values(det, "ABCDIOSFODNN7EXAMPLE") == []

    def test_aws_key_location(self):
        det = AWSAccessKeyDetector()
        text = "key=AKIAIOSFODNN7EXAMPLE rest"
        m = _first_match(det, text)
        assert m is not None
        assert text[m.start : m.end] == "AKIAIOSFODNN7EXAMPLE"


# ═══════════════════════════════════════════════════════════════════════════
# OPENAI API KEY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestOpenAIKeyDetector:
    """Tests for OpenAIKeyDetector."""

    def test_legacy_sk_key_detection(self):
        det = OpenAIKeyDetector()
        key = "sk-" + "a" * 48
        found = _values(det, f"OPENAI_API_KEY={key}")
        assert key in found

    def test_project_sk_key_detection(self):
        det = OpenAIKeyDetector()
        key = "sk-proj-" + "A1b2C3d4E5f6G7h8" * 3
        found = _values(det, f"key: {key}")
        assert key in found

    def test_svcacct_key_detection(self):
        det = OpenAIKeyDetector()
        key = "sk-svcacct-" + "x" * 30
        found = _values(det, f"token={key}")
        assert key in found

    def test_project_key_highest_confidence(self):
        det = OpenAIKeyDetector()
        key = "sk-proj-" + "A" * 30
        m = _first_match(det, key)
        assert m is not None
        assert m.confidence == 0.99

    def test_svcacct_key_highest_confidence(self):
        det = OpenAIKeyDetector()
        key = "sk-svcacct-" + "B" * 30
        m = _first_match(det, key)
        assert m is not None
        assert m.confidence == 0.99

    def test_legacy_key_high_confidence(self):
        det = OpenAIKeyDetector()
        key = "sk-" + "c" * 48
        m = _first_match(det, key)
        assert m is not None
        assert m.confidence == 0.97

    def test_openai_key_label(self):
        det = OpenAIKeyDetector()
        key = "sk-" + "d" * 48
        m = _first_match(det, key)
        assert m is not None
        assert m.label == "OPENAI_KEY"

    def test_openai_key_replacement_tag(self):
        det = OpenAIKeyDetector()
        key = "sk-" + "e" * 48
        m = _first_match(det, key)
        assert m is not None
        assert m.replacement == "[OPENAI_KEY_REDACTED]"

    def test_org_id_detection(self):
        det = OpenAIKeyDetector()
        org = "org-" + "A" * 24
        matches = det.detect(f"organization: {org}")
        org_matches = [m for m in matches if m.label == "OPENAI_ORG"]
        assert len(org_matches) == 1
        assert org_matches[0].value == org

    def test_org_id_confidence(self):
        det = OpenAIKeyDetector()
        org = "org-" + "B" * 24
        matches = det.detect(org)
        org_matches = [m for m in matches if m.label == "OPENAI_ORG"]
        assert len(org_matches) == 1
        assert org_matches[0].confidence == 0.85

    def test_openai_key_output_format(self):
        det = OpenAIKeyDetector()
        key = "sk-proj-" + "F" * 30
        m = _first_match(det, key)
        assert m is not None
        d = m.to_dict()
        assert d["type"] == "OPENAI_KEY"
        assert d["confidence"] == 0.99
        assert d["replacement"] == "[OPENAI_KEY_REDACTED]"

    def test_no_false_positive_on_short_sk(self):
        det = OpenAIKeyDetector()
        # Too short — under 20 chars after "sk-"
        assert _values(det, "sk-short") == []


# ═══════════════════════════════════════════════════════════════════════════
# GENERIC API KEY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestGenericAPIKeyDetector:
    """Tests for GenericAPIKeyDetector."""

    def test_github_pat_detection(self):
        det = GenericAPIKeyDetector()
        token = "ghp_" + "A" * 36
        found = _values(det, f"token: {token}")
        assert token in found

    def test_gitlab_pat_detection(self):
        det = GenericAPIKeyDetector()
        token = "glpat-" + "B" * 20
        found = _values(det, f"GITLAB_TOKEN={token}")
        assert token in found

    def test_slack_token_detection(self):
        det = GenericAPIKeyDetector()
        token = "xoxb-" + "C" * 20
        found = _values(det, f"slack: {token}")
        assert token in found

    def test_stripe_live_key_detection(self):
        det = GenericAPIKeyDetector()
        token = "sk_live_" + "D" * 24
        found = _values(det, f"STRIPE_KEY={token}")
        assert token in found

    def test_bearer_token_detection(self):
        det = GenericAPIKeyDetector()
        token = "A" * 40
        text = f"Authorization: Bearer {token}"
        found = _values(det, text)
        assert token in found

    def test_context_based_api_key_detection(self):
        det = GenericAPIKeyDetector()
        # High-entropy value after a config key
        key = "aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV"
        text = f'api_key = "{key}"'
        found = _values(det, text)
        assert key in found

    def test_generic_api_key_label(self):
        det = GenericAPIKeyDetector()
        token = "ghp_" + "E" * 36
        m = _first_match(det, token)
        assert m is not None
        assert m.label == "API_KEY"

    def test_generic_api_key_replacement_tag(self):
        det = GenericAPIKeyDetector()
        token = "ghp_" + "F" * 36
        m = _first_match(det, token)
        assert m is not None
        assert m.replacement == "[API_KEY_REDACTED]"

    def test_prefixed_keys_higher_confidence(self):
        det = GenericAPIKeyDetector()
        token = "ghp_" + "G" * 36
        m = _first_match(det, token)
        assert m is not None
        assert m.confidence == 0.95  # Prefixed keys

    def test_bearer_token_confidence(self):
        det = GenericAPIKeyDetector()
        token = "H" * 40
        m = _first_match(det, f"Bearer {token}")
        assert m is not None
        assert m.confidence == 0.90

    def test_no_false_positive_on_normal_text(self):
        det = GenericAPIKeyDetector()
        assert _values(det, "This is a normal sentence with no secrets.") == []

    def test_no_false_positive_on_short_values(self):
        det = GenericAPIKeyDetector()
        assert _values(det, "api_key = short") == []

    def test_shannon_entropy_high_for_random(self):
        # Random-looking string should have high entropy
        assert _shannon_entropy("aB3cD4eF5gH6iJ7kL8mN") > 3.5

    def test_shannon_entropy_low_for_repetitive(self):
        # Repetitive string should have low entropy
        assert _shannon_entropy("aaaaaaaaaa") < 1.0

    def test_hex_token_detection(self):
        det = GenericAPIKeyDetector()
        # 32-char hex token with high entropy
        token = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        text = f"debug token: {token}"
        found = _values(det, text)
        assert token in found

    def test_generic_key_output_format(self):
        det = GenericAPIKeyDetector()
        token = "ghp_" + "X" * 36
        m = _first_match(det, token)
        assert m is not None
        d = m.to_dict()
        assert d["type"] == "API_KEY"
        assert d["confidence"] == 0.95
        assert d["replacement"] == "[API_KEY_REDACTED]"

    def test_sendgrid_key_detection(self):
        det = GenericAPIKeyDetector()
        token = "SG." + "A" * 22 + "." + "B" * 22
        found = _values(det, f"sendgrid: {token}")
        assert token in found


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY & FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistry:
    """Tests for the detector registry and factory functions."""

    def test_all_detectors_registered(self):
        expected = {
            "email", "phone", "ipv4", "ipv6", "credit_card", "ssn",
            "jwt", "aws_key", "openai_key", "generic_api_key",
        }
        assert expected == set(REGISTRY.keys())

    def test_build_detectors_unknown_raises(self):
        with pytest.raises(KeyError):
            build_detectors(["email", "not-a-detector"])

    def test_default_detectors_count(self):
        detectors = default_detectors()
        assert len(detectors) == 10

    def test_available_detectors_sorted(self):
        names = available_detectors()
        assert names == sorted(names)
        assert len(names) == 10

    def test_build_specific_detectors(self):
        detectors = build_detectors(["email", "jwt", "aws_key"])
        labels = {d.label for d in detectors}
        assert "EMAIL" in labels
        assert "JWT" in labels
        assert "AWS_KEY" in labels


# ═══════════════════════════════════════════════════════════════════════════
# MATCH DATACLASS TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestMatchDataclass:
    """Tests for the Match dataclass."""

    def test_match_invalid_span_raises(self):
        from pii_scrub_stream.detectors.base import Match

        with pytest.raises(ValueError):
            Match(start=5, end=3, value="x", label="X")

    def test_match_negative_start_raises(self):
        from pii_scrub_stream.detectors.base import Match

        with pytest.raises(ValueError):
            Match(start=-1, end=3, value="x", label="X")

    def test_match_invalid_confidence_raises(self):
        from pii_scrub_stream.detectors.base import Match

        with pytest.raises(ValueError):
            Match(start=0, end=1, value="x", label="X", confidence=1.5)

    def test_match_length_property(self):
        from pii_scrub_stream.detectors.base import Match

        m = Match(start=10, end=20, value="0123456789", label="TEST")
        assert m.length == 10

    def test_match_to_dict(self):
        from pii_scrub_stream.detectors.base import Match

        m = Match(
            start=0, end=5, value="hello", label="TEST",
            confidence=0.88, replacement="[TEST_REDACTED]",
        )
        d = m.to_dict()
        assert d == {
            "match": "hello",
            "type": "TEST",
            "start": 0,
            "end": 5,
            "confidence": 0.88,
            "replacement": "[TEST_REDACTED]",
        }

    def test_match_frozen(self):
        from pii_scrub_stream.detectors.base import Match

        m = Match(start=0, end=1, value="x", label="X")
        with pytest.raises(AttributeError):
            m.value = "y"  # type: ignore[misc]
