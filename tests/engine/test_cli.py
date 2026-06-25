"""Unit tests for the Click CLI."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from redactai.engine.cli.main import cli


def test_scrub_single_file(tmp_path: Path):
    src = tmp_path / "in.log"
    dst = tmp_path / "out.log"
    src.write_text("login a@b.com from 10.0.0.1\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["scrub", str(src), str(dst)])

    assert result.exit_code == 0, result.output
    assert "redactions" in result.output
    content = dst.read_text(encoding="utf-8")
    assert "a@b.com" not in content
    assert "10.0.0.1" not in content


def test_scrub_with_specific_detector(tmp_path: Path):
    src = tmp_path / "in.log"
    dst = tmp_path / "out.log"
    src.write_text("a@b.com 10.0.0.1\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["scrub", str(src), str(dst), "-d", "email"])

    assert result.exit_code == 0, result.output
    content = dst.read_text(encoding="utf-8")
    assert "a@b.com" not in content
    # ipv4 detector not enabled, so the IP should survive
    assert "10.0.0.1" in content


def test_scrub_unknown_detector_errors(tmp_path: Path):
    src = tmp_path / "in.log"
    src.write_text("x\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["scrub", str(src), str(tmp_path / "o.log"), "-d", "bogus"])
    assert result.exit_code != 0
    assert "Unknown detector" in result.output


def test_scrub_mask_mode(tmp_path: Path):
    src = tmp_path / "in.log"
    dst = tmp_path / "out.log"
    src.write_text("mail a@b.com\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["scrub", str(src), str(dst), "--mask", "-d", "email"])
    assert result.exit_code == 0, result.output
    out = dst.read_text(encoding="utf-8")
    assert "*" in out and "a@b.com" not in out


def test_batch_processes_multiple_files(tmp_path: Path):
    out_dir = tmp_path / "out"
    inputs = []
    for i in range(3):
        p = tmp_path / f"in_{i}.log"
        p.write_text(f"user user{i}@ex.com\n", encoding="utf-8")
        inputs.append(str(p))

    runner = CliRunner()
    result = runner.invoke(cli, ["batch", *inputs, "-o", str(out_dir), "-w", "3"])

    assert result.exit_code == 0, result.output
    produced = sorted(out_dir.glob("*.scrubbed.log"))
    assert len(produced) == 3
    for f in produced:
        assert "@ex.com" not in f.read_text(encoding="utf-8")


def test_detectors_command_lists_names():
    runner = CliRunner()
    result = runner.invoke(cli, ["detectors"])
    assert result.exit_code == 0
    assert "email" in result.output
    assert "credit_card" in result.output


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    # The output will contain 'redactai' because that's the prog name
    assert "redactai" in result.output.lower()
