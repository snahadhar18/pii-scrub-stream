"""Exception hierarchy for RedactAI.

A single rooted hierarchy lets callers catch :class:`RagGuardianError` to handle
*any* expected failure from the library, while still allowing fine-grained
handling of specific failure modes (configuration, ingestion, processing).
"""

from __future__ import annotations


class RagGuardianError(Exception):
    """Base class for every error raised by RedactAI."""


class ConfigurationError(RagGuardianError):
    """Raised when configuration is missing or invalid."""


class IngestionError(RagGuardianError):
    """Raised when a source cannot be read or parsed."""


class ProcessingError(RagGuardianError):
    """Raised when the processing engine fails to handle a record."""


class DetectorError(RagGuardianError):
    """Raised when a detector plugin is missing or misbehaves.

    Note: this signals an *infrastructure* problem with a detector (e.g. it
    raised an exception or is not registered), never a detection result.
    """
