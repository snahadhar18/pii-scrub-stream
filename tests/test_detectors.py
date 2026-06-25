"""Unit tests for the individual detectors."""

from __future__ import annotations

import pytest

from pii_scrub_stream.detectors import build_detectors, default_detectors
from pii_scrub_stream.detectors.credit_card import CreditCardDetector, luhn_checksum_valid
from pii_scrub_stream.detectors.email import EmailDetector
from pii_scrub_stream.detectors.ip import IPv4Detector, IPv6Detector
from pii_scrub_stream.detectors.phone import PhoneDetector
from pii_scrub_stream.detectors.ssn import SSNDetector


def _values(detector, text):
    return [m.value for m in detector.detect(text)]


def test_email_detection():
    det = EmailDetector()
    found = _values(det, "Contact alice@example.com or bob.smith+tag@sub.domain.io please.")
    assert "alice@example.com" in found
    assert "bob.smith+tag@sub.domain.io" in found


def test_email_labels_match():
    det = EmailDetector()
    matches = det.detect("x@y.com")
    assert matches and matches[0].label == "EMAIL"
    assert matches[0].value == "x@y.com"
    assert (matches[0].start, matches[0].end) == (0, 7)


@pytest.mark.parametrize(
    "text",
    [
        "Call +1 (555) 123-4567 now",
        "phone: 555-123-4567",
        "tel 555.123.4567",
    ],
)
def test_phone_detection(text):
    det = PhoneDetector()
    assert _values(det, text), f"expected a phone match in {text!r}"


def test_phone_ignores_short_numbers():
    det = PhoneDetector()
    assert _values(det, "order 12345 shipped") == []


def test_ipv4_detection():
    det = IPv4Detector()
    found = _values(det, "src=192.168.0.1 dst=255.255.255.255 bad=999.1.1.1")
    assert "192.168.0.1" in found
    assert "255.255.255.255" in found
    assert "999.1.1.1" not in found


def test_ipv6_detection():
    det = IPv6Detector()
    found = _values(det, "addr 2001:db8::1 here")
    assert any("2001:db8" in v for v in found)


def test_credit_card_luhn_validation():
    det = CreditCardDetector()
    # 4111 1111 1111 1111 is a well-known Luhn-valid test number.
    assert _values(det, "card 4111 1111 1111 1111") == ["4111 1111 1111 1111"]
    # A non-Luhn 16-digit string must be rejected.
    assert _values(det, "card 1234 5678 9012 3456") == []


def test_luhn_helper():
    assert luhn_checksum_valid("4111111111111111")
    assert not luhn_checksum_valid("4111111111111112")
    assert not luhn_checksum_valid("123")


def test_ssn_detection():
    det = SSNDetector()
    found = _values(det, "ssn 123-45-6789 and 078-05-1120")
    assert "123-45-6789" in found


def test_ssn_rejects_invalid_area():
    det = SSNDetector()
    assert _values(det, "000-12-3456") == []


def test_build_detectors_unknown_raises():
    with pytest.raises(KeyError):
        build_detectors(["email", "not-a-detector"])


def test_default_detectors_nonempty():
    assert len(default_detectors()) >= 5
