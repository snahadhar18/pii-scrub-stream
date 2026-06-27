"""GitHub token detector."""

import re

from redactai.engine.detectors.base import RegexDetector

_GITHUB_TOKEN_RE = re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,})\b")


class GitHubTokenDetector(RegexDetector):
    """Detect GitHub Personal Access Tokens and other GitHub tokens."""

    label = "GITHUB_TOKEN"
    pattern = _GITHUB_TOKEN_RE
    default_confidence = 0.99
    default_severity = "CRITICAL"
