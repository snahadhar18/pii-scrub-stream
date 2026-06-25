"""Typed, environment-driven configuration.

All tunables live here as nested Pydantic models so they are validated once, at
startup, and injected everywhere else. Settings load from (in order of
precedence): explicit constructor args, environment variables, then a ``.env``
file. Environment variables use the ``RG_`` prefix and ``__`` as the nested
delimiter, e.g. ``RG_PROCESSING__WORKERS=8`` or ``RG_API__PORT=9000``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from redactai.gateway.core.redaction import RedactionStrategy


class ProcessingSettings(BaseModel):
    """Concurrency and batching knobs for the processing engine."""

    workers: int = Field(default=4, ge=1, le=512, description="ThreadPoolExecutor size.")
    batch_size: int = Field(default=256, ge=1, description="Records grouped per work unit.")
    queue_maxsize: int = Field(
        default=1000, ge=1, description="Bounded queue depth; provides backpressure."
    )
    max_retries: int = Field(default=2, ge=0, description="Retries per record on transient errors.")
    redaction_strategy: RedactionStrategy = RedactionStrategy.TAG
    redact_by_default: bool = Field(default=True, description="Emit redacted content by default.")


class StreamingSettings(BaseModel):
    """Real-time stdin/stream processing knobs."""

    buffer_size: int = Field(default=1000, ge=1, description="In-flight line buffer size.")
    workers: int = Field(default=2, ge=1, description="Stream worker pool size.")
    flush_interval_ms: int = Field(default=250, ge=0, description="Max latency before flushing.")
    shutdown_grace_s: float = Field(default=5.0, ge=0, description="Drain time on shutdown.")


class IngestionSettings(BaseModel):
    """File/CSV/JSON ingestion knobs."""

    chunk_size: int = Field(default=65536, ge=1, description="Bytes per read for streamed files.")
    encoding: str = Field(default="utf-8", description="Default text encoding.")
    csv_delimiter: str = Field(default=",", description="Default CSV delimiter.")
    max_record_bytes: int = Field(
        default=10 * 1024 * 1024, ge=1, description="Reject pathologically large single records."
    )


class APISettings(BaseModel):
    """FastAPI server knobs."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    title: str = "RedactAI"
    cors_origins: tuple[str, ...] = ("*",)
    max_request_bytes: int = Field(default=5 * 1024 * 1024, ge=1)


class ObservabilitySettings(BaseModel):
    """Logging, metrics and audit configuration."""

    log_level: str = Field(default="INFO", description="Root log level.")
    log_format: str = Field(default="json", description="'json' or 'text'.")
    audit_enabled: bool = True
    audit_path: str | None = Field(
        default=None, description="File for audit events; stdout when unset."
    )
    metrics_enabled: bool = True


class Settings(BaseSettings):
    """Root application settings, composed of the sections above."""

    model_config = SettingsConfigDict(
        env_prefix="RG_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", description="deployment environment name.")
    detectors: tuple[str, ...] = Field(
        default=(),
        description="Names of registered detectors to enable; empty enables all discovered.",
    )
    load_entry_point_detectors: bool = Field(
        default=True, description="Auto-discover detectors via entry points at startup."
    )

    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    streaming: StreamingSettings = Field(default_factory=StreamingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    api: APISettings = Field(default_factory=APISettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (process singleton)."""
    return Settings()


__all__ = [
    "Settings",
    "ProcessingSettings",
    "StreamingSettings",
    "IngestionSettings",
    "APISettings",
    "ObservabilitySettings",
    "get_settings",
]
