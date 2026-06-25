"""Tests for the ingestion sources and factory."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from redactai.gateway.core.exceptions import IngestionError
from redactai.gateway.ingestion.csv_source import CSVSource
from redactai.gateway.ingestion.factory import SourceFactory, SourceType
from redactai.gateway.ingestion.file_source import FileSource
from redactai.gateway.ingestion.json_source import JSONSource


def test_file_source_streams_lines(tmp_path: Path) -> None:
    p = tmp_path / "app.log"
    p.write_text("line one\nline two\n\nline four\n", encoding="utf-8")
    with FileSource(p, skip_blank=True) as src:
        records = list(src)
    assert [r.content for r in records] == ["line one", "line two", "line four"]
    assert records[0].offset == 1
    assert records[-1].source == str(p)


def test_file_source_missing_file(tmp_path: Path) -> None:
    with pytest.raises(IngestionError), FileSource(tmp_path / "nope.txt") as src:
        list(src)


def test_csv_source_with_header(tmp_path: Path) -> None:
    p = tmp_path / "users.csv"
    p.write_text("name,email\nAlice,a@b.com\nBob,b@c.com\n", encoding="utf-8")
    with CSVSource(p) as src:
        records = list(src)
    assert len(records) == 2
    assert records[0].metadata["fields"]["email"] == "a@b.com"
    assert records[0].offset == 2  # header is row 1


def test_csv_source_selected_columns(tmp_path: Path) -> None:
    p = tmp_path / "users.csv"
    p.write_text("name,email\nAlice,a@b.com\n", encoding="utf-8")
    with CSVSource(p, columns=["email"]) as src:
        records = list(src)
    assert records[0].content == "a@b.com"


def test_json_lines_source(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    p.write_text('{"msg": "hi"}\n{"msg": "bye"}\n', encoding="utf-8")
    with JSONSource(p, content_field="msg") as src:
        records = list(src)
    assert [r.content for r in records] == ["hi", "bye"]


def test_json_array_source(tmp_path: Path) -> None:
    p = tmp_path / "data.json"
    p.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
    with JSONSource(p) as src:
        records = list(src)
    assert len(records) == 2
    assert json.loads(records[0].content) == {"a": 1}


def test_factory_infers_type(tmp_path: Path) -> None:
    assert SourceType.from_suffix(Path("x.csv")) is SourceType.CSV
    assert SourceType.from_suffix(Path("x.jsonl")) is SourceType.JSON
    assert SourceType.from_suffix(Path("x.log")) is SourceType.TEXT
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    src = SourceFactory().for_path(p)
    assert isinstance(src, CSVSource)


def test_async_iteration(tmp_path: Path) -> None:
    p = tmp_path / "a.log"
    p.write_text("x\ny\nz\n", encoding="utf-8")

    async def collect() -> list[str]:
        out: list[str] = []
        async with FileSource(p) as src:
            async for record in src.aiter_records(chunk=2):
                out.append(record.content)
        return out

    assert asyncio.run(collect()) == ["x", "y", "z"]
