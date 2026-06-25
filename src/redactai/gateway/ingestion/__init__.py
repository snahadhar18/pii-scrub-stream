"""Ingestion layer: pluggable, memory-efficient record sources.

Every source converts some external representation (a text/log file, a CSV, a
JSON document or stream) into a uniform stream of :class:`Record` objects that
the processing engine can consume. Sources are lazy and chunked so a multi-
gigabyte file never has to be resident in memory.
"""

from __future__ import annotations

from redactai.gateway.ingestion.base import BaseIngestionSource
from redactai.gateway.ingestion.csv_source import CSVSource
from redactai.gateway.ingestion.factory import SourceFactory, SourceType
from redactai.gateway.ingestion.file_source import FileSource
from redactai.gateway.ingestion.json_source import JSONSource

__all__ = [
    "BaseIngestionSource",
    "FileSource",
    "CSVSource",
    "JSONSource",
    "SourceFactory",
    "SourceType",
]
