# pii-scrub-stream

A production-ready CLI tool that **streams** text and log files and **redacts
sensitive information** (PII) — emails, phone numbers, IP addresses, credit
cards, and US SSNs — using a modular, extensible detector architecture.

Because files are processed line-by-line, `pii-scrub-stream` handles
arbitrarily large logs in constant memory, and it can scrub many files in
parallel with a thread pool.

## Features

- **Streaming redaction** — bounded memory regardless of file size.
- **Pluggable detectors** — implement one method to add a new PII type.
- **Luhn-validated** credit-card detection to cut false positives.
- **Concurrent batch mode** powered by `ThreadPoolExecutor`.
- **Two redaction strategies** — typed placeholders (`[REDACTED_EMAIL]`) or
  masking (`****`, optionally keeping the last N characters).
- **Clean Click CLI** with `scrub`, `batch`, and `detectors` commands.

## Installation

```bash
# from the project root
python -m pip install -e ".[dev]"
```

This installs the `pii-scrub` console script.

## Usage

Scrub a single file (the canonical command):

```bash
pii-scrub scrub input.log output.log
```

Use only specific detectors:

```bash
pii-scrub scrub input.log output.log -d email -d ipv4
```

Mask instead of labelling, keeping the last 4 characters:

```bash
pii-scrub scrub input.log output.log --mask --keep-last 4
```

Scrub many files concurrently into a directory:

```bash
pii-scrub batch logs/*.log -o scrubbed/ --workers 8
```

List available detectors:

```bash
pii-scrub detectors
```

## Project layout

```text
pii-scrub-stream/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/pii_scrub_stream/
    ├── cli/            # Click command-line interface
    │   └── main.py
    ├── scrubber/       # Redaction engine + strategies
    │   ├── engine.py
    │   └── redaction.py
    └── detectors/      # Detector interface + built-ins
        ├── base.py
        ├── email.py
        ├── phone.py
        ├── ip.py
        ├── credit_card.py
        └── ssn.py
tests/                  # pytest unit tests
```

## The detector interface

Every detector implements a single method that maps text to a list of matches:

```python
from pii_scrub_stream.detectors.base import Detector, Match

class Detector:
    label: str = "GENERIC"

    def detect(self, text: str) -> list[Match]:
        ...
```

A `Match` is an immutable span: `start`, `end`, `value`, and `label`.

### Writing a custom detector

Most detectors are regex-based, so subclass `RegexDetector` and (optionally)
add secondary validation:

```python
import re
from pii_scrub_stream.detectors.base import RegexDetector

class ApiKeyDetector(RegexDetector):
    label = "API_KEY"
    pattern = re.compile(r"\bsk-[A-Za-z0-9]{32}\b")

    def validate(self, value: str) -> bool:
        return value.startswith("sk-")
```

Then register it:

```python
from pii_scrub_stream.detectors import REGISTRY
REGISTRY["api_key"] = ApiKeyDetector
```

## The redaction engine

`RedactionEngine` accepts any number of detectors plus a redaction strategy:

```python
from pii_scrub_stream import RedactionEngine
from pii_scrub_stream.detectors import default_detectors

engine = RedactionEngine(default_detectors())

clean, count = engine.scrub_text("email a@b.com ip 10.0.0.1")
# -> ("email [REDACTED_EMAIL] ip [REDACTED_IPV4]", 2)

# Concurrent file processing (I/O bound -> threads).
results = engine.scrub_files(
    [("a.log", "a.out"), ("b.log", "b.out")],
    max_workers=8,
)
```

Overlapping matches from different detectors are resolved deterministically
(earliest start wins; ties go to the longer span).

## Development

```bash
python -m pip install -e ".[dev]"
pytest                 # run the test suite
ruff check .           # lint
mypy src               # type-check
```

## Contributing

Contributions are welcome! Please open an issue or pull request. New detectors
should ship with unit tests and be added to the `REGISTRY`.

## License

MIT — see [LICENSE](LICENSE).
