"""Redaction strategies: turn a detected :class:`Match` into replacement text."""

from __future__ import annotations

from collections.abc import Callable

from redactai.engine.detectors.base import Match

#: A redactor maps a match to the string that should replace it.
Redactor = Callable[[Match], str]


def label_redactor(match: Match) -> str:
    """Replace the match with a typed placeholder, e.g. ``[REDACTED_EMAIL]``."""
    return f"[REDACTED_{match.label}]"


def fixed_redactor(match: Match, replacement: str = "[REDACTED]") -> str:
    """Replace the match with a single fixed token."""
    return replacement


def make_mask_redactor(mask_char: str = "*", keep_last: int = 0) -> Redactor:
    """Build a redactor that masks characters while optionally keeping a suffix.

    Args:
        mask_char: Character used for masked positions.
        keep_last: Number of trailing characters to preserve (useful for the
            last 4 digits of a card). Non-digit characters in the suffix are
            preserved as-is.
    """
    if keep_last < 0:
        raise ValueError("keep_last must be non-negative")

    def _mask(match: Match) -> str:
        value = match.value
        if keep_last == 0:
            return mask_char * len(value)
        visible = value[-keep_last:] if keep_last < len(value) else value
        hidden_len = max(len(value) - len(visible), 0)
        return mask_char * hidden_len + visible

    return _mask
