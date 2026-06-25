"""Unit tests for the redaction engine."""

from __future__ import annotations

import io

import pytest

from pii_scrub_stream.detectors.base import Match
from pii_scrub_stream.detectors.email_detector import EmailDetector
from pii_scrub_stream.detectors.ip_detector import IPv4Detector
from pii_scrub_stream.scrubber.engine import RedactionEngine, resolve_overlaps
from pii_scrub_stream.scrubber.redaction import label_redactor, make_mask_redactor


def make_engine(**kwargs):
    return RedactionEngine([EmailDetector(), IPv4Detector()], **kwargs)


def test_requires_at_least_one_detector():
    with pytest.raises(ValueError):
        RedactionEngine([])


def test_scrub_text_replaces_with_labels():
    engine = make_engine()
    text = "user a@b.com from 10.0.0.1"
    redacted, count = engine.scrub_text(text)
    assert count == 2
    assert "a@b.com" not in redacted
    assert "10.0.0.1" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_IPV4]" in redacted


def test_scrub_text_no_matches_returns_input():
    engine = make_engine()
    text = "nothing sensitive here"
    assert engine.scrub_text(text) == (text, 0)


def test_mask_redactor_keep_last():
    engine = RedactionEngine([EmailDetector()], redactor=make_mask_redactor(keep_last=0))
    redacted, _ = engine.scrub_text("hi a@b.com")
    assert "*" in redacted and "a@b.com" not in redacted


def test_resolve_overlaps_prefers_earliest_then_longest():
    matches = [
        Match(0, 5, "aaaaa", "A", 0.9, "[A_REDACTED]"),
        Match(2, 9, "longerB", "B", 0.9, "[B_REDACTED]"),  # overlaps with first
        Match(10, 12, "cc", "C", 0.9, "[C_REDACTED]"),
    ]
    resolved = resolve_overlaps(matches)
    assert [m.label for m in resolved] == ["A", "C"]


def test_resolve_overlaps_empty():
    assert resolve_overlaps([]) == []


def test_scrub_stream_counts_and_writes():
    engine = make_engine()
    source = ["line a@b.com\n", "clean line\n", "ip 1.2.3.4\n"]
    sink = io.StringIO()
    total = engine.scrub_stream(source, sink)
    assert total == 2
    out = sink.getvalue()
    assert out.count("\n") == 3
    assert "a@b.com" not in out


def test_scrub_file_roundtrip(tmp_path):
    src = tmp_path / "in.log"
    dst = tmp_path / "out.log"
    src.write_text("contact a@b.com\n", encoding="utf-8")
    engine = make_engine()
    result = engine.scrub_file(src, dst)
    assert result.ok
    assert result.matches == 1
    assert "a@b.com" not in dst.read_text(encoding="utf-8")


def test_scrub_files_concurrent(tmp_path):
    inputs = []
    jobs = []
    for i in range(5):
        p = tmp_path / f"in_{i}.log"
        p.write_text(f"user user{i}@ex.com ip 10.0.0.{i}\n", encoding="utf-8")
        out = tmp_path / f"out_{i}.log"
        inputs.append(p)
        jobs.append((p, out))

    engine = make_engine()
    results = engine.scrub_files(jobs, max_workers=4)
    assert len(results) == 5
    assert all(r.ok for r in results)
    assert all(r.matches == 2 for r in results)
    for _, out in jobs:
        assert "@ex.com" not in out.read_text(encoding="utf-8")


def test_scrub_files_empty_jobs():
    engine = make_engine()
    assert engine.scrub_files([]) == []


def test_scrub_file_missing_input_reports_error(tmp_path):
    engine = make_engine()
    result = engine.scrub_file(tmp_path / "nope.log", tmp_path / "out.log")
    assert not result.ok
    assert result.error


def test_find_matches_returns_confidence():
    """Verify that matches from the engine carry confidence scores."""
    engine = make_engine()
    matches = engine.find_matches("a@b.com from 10.0.0.1")
    assert len(matches) == 2
    for m in matches:
        assert 0.0 <= m.confidence <= 1.0
        assert m.replacement != ""


def test_find_matches_returns_replacement_tags():
    """Verify that each match has a typed replacement tag."""
    engine = make_engine()
    matches = engine.find_matches("a@b.com")
    assert len(matches) == 1
    assert matches[0].replacement == "[EMAIL_REDACTED]"
