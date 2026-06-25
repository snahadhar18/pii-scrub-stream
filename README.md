# redactai

A production-ready CLI tool that **streams** text and log files and **redacts
sensitive information** (PII) — emails, phone numbers, IP addresses, credit
cards, US SSNs, JWT tokens, AWS keys, OpenAI API keys, and generic API
secrets — using a modular, extensible detector architecture.

Because files are processed line-by-line, `redactai` handles
arbitrarily large logs in constant memory, and it can scrub many files in
parallel with a thread pool.

## Features

- **Streaming redaction** — bounded memory regardless of file size.
- **Pluggable detectors** — implement one method to add a new PII type.
- **10 built-in detectors** — email, phone, IPv4, IPv6, credit card (Luhn-validated), SSN, JWT, AWS keys, OpenAI keys, and generic API keys.
- **Confidence scoring** — each detection returns a confidence score (0.0–1.0) for downstream filtering.
- **Luhn-validated** credit-card detection to cut false positives.
- **JWT header validation** — decodes and validates JWT headers for high-confidence detection.
- **Shannon entropy analysis** — generic API key detector uses entropy to identify machine-generated secrets.
- **Concurrent batch mode** powered by `ThreadPoolExecutor`.
- **Two redaction strategies** — typed placeholders (`[EMAIL_REDACTED]`) or
  masking (`****`, optionally keeping the last N characters).
- **Clean Click CLI** with `scrub`, `batch`, and `detectors` commands.

## RedactAI — infrastructure gateway

This repository also includes **RedactAI** (`redactai.gateway/`), an
enterprise-grade AI security gateway that provides the *infrastructure* around
detection — file/CSV/JSON ingestion, a concurrent processing engine, real-time
streaming, a FastAPI service, observability, Docker, CI/CD and a horizontal
scaling layer — all built around a single pluggable detector contract. It ships
**no detection logic**; detectors are external plugins.

```bash
pip install -e ".[api,json]"
redactai detectors                       # list registered plugins
tail -f app.log | redactai stream        # real-time redacting filter
redactai serve --port 8000               # POST /scan /stream /ingest, GET /health /metrics
```

See [`redactai.gateway/docs/README.md`](redactai.gateway/docs/README.md),
[`architecture.md`](redactai.gateway/docs/architecture.md), and
[`scalability.md`](redactai.gateway/docs/scalability.md).

## Built-in Detectors

| Detector | Label | Confidence | What it catches |
|---|---|---|---|
| `email` | `EMAIL` | 0.99 | RFC-5322-ish email addresses |
| `phone` | `PHONE` | 0.85–0.95 | North-American and international phone numbers |
| `credit_card` | `CREDIT_CARD` | 0.95–0.99 | Luhn-validated card numbers (Visa, MC, Amex, Discover) |
| `ipv4` | `IPV4` | 0.95 | IPv4 addresses |
| `ipv6` | `IPV6` | 0.90 | IPv6 addresses |
| `ssn` | `SSN` | 0.85–0.95 | US Social Security Numbers |
| `jwt` | `JWT` | 0.90–0.99 | JSON Web Tokens |
| `aws_key` | `AWS_KEY` | 0.95–0.99 | AWS Access Key IDs (AKIA/ASIA) and Secret Keys |
| `openai_key` | `OPENAI_KEY` | 0.85–0.99 | OpenAI API keys (sk-/sk-proj-/sk-svcacct-/org-) |
| `generic_api_key` | `API_KEY` | 0.75–0.95 | GitHub, GitLab, Slack, Stripe, SendGrid tokens, Bearer tokens, and high-entropy secrets |

## Installation

```bash
# from the project root
python -m pip install -e ".[dev]"
```

This installs the `redactai-engine` console script.

## Usage

Scrub a single file (the canonical command):

```bash
redactai-engine scrub input.log output.log
```

Use only specific detectors:

```bash
redactai-engine scrub input.log output.log -d email -d ipv4 -d jwt
```

Mask instead of labelling, keeping the last 4 characters:

```bash
redactai-engine scrub input.log output.log --mask --keep-last 4
```

Scrub many files concurrently into a directory:

```bash
redactai-engine batch logs/*.log -o scrubbed/ --workers 8
```

List available detectors:

```bash
redactai-engine detectors
```

## Detection Output Format

Each detection produces a structured result:

```json
{
  "match": "john@gmail.com",
  "type": "EMAIL",
  "start": 10,
  "end": 24,
  "confidence": 0.99,
  "replacement": "[EMAIL_REDACTED]"
}
```

## Project layout

```text
redactai/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/redactai/engine/
    ├── cli/            # Click command-line interface
    │   └── main.py
    ├── scrubber/       # Redaction engine + strategies
    │   ├── engine.py
    │   └── redaction.py
    └── detectors/      # Detector interface + built-ins
        ├── base.py           # Detector, RegexDetector, Match
        ├── email.py          # EmailDetector
        ├── phone.py          # PhoneDetector
        ├── ip.py             # IPv4Detector, IPv6Detector
        ├── credit_card.py    # CreditCardDetector (Luhn)
        ├── ssn.py            # SSNDetector
        ├── jwt.py            # JWTDetector
        ├── aws_key.py        # AWSAccessKeyDetector
        ├── openai_key.py     # OpenAIKeyDetector
        └── generic_api_key.py # GenericAPIKeyDetector
tests/                  # pytest unit tests
```

## The detector interface

Every detector implements a single method that maps text to a list of matches:

```python
from redactai.engine.detectors.base import Detector, Match

class Detector:
    label: str = "GENERIC"

    def detect(self, text: str) -> list[Match]:
        ...
```

A `Match` is an immutable dataclass with fields: `start`, `end`, `value`,
`label`, `confidence`, and `replacement`.

### Writing a custom detector

Most detectors are regex-based, so subclass `RegexDetector` and (optionally)
add secondary validation:

```python
import re
from redactai.engine.detectors.base import RegexDetector

class ApiKeyDetector(RegexDetector):
    label = "API_KEY"
    pattern = re.compile(r"\bsk-[A-Za-z0-9]{32}\b")
    default_confidence = 0.95

    def validate(self, value: str) -> bool:
        return value.startswith("sk-")
```

Then register it:

```python
from redactai.engine.detectors import REGISTRY
REGISTRY["api_key"] = ApiKeyDetector
```

## The redaction engine

`RedactionEngine` accepts any number of detectors plus a redaction strategy:

```python
from redactai.engine import RedactionEngine
from redactai.engine.detectors import default_detectors

engine = RedactionEngine(default_detectors())

clean, count = engine.scrub_text("email a@b.com ip 10.0.0.1")
# -> ("email [REDACTED_EMAIL] ip [REDACTED_IPV4]", 2)

# Get structured match objects with confidence scores
matches = engine.find_matches("email john@gmail.com token AKIAIOSFODNN7EXAMPLE")
for m in matches:
    print(m.to_dict())

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

## Authors

- **snahadhar18** — creator and maintainer
- **Prakhar SHUKLA** (pss317@uowmail.edu.au) — co-author

## License

MIT — see [LICENSE](LICENSE).
