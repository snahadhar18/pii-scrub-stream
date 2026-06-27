# Installation Guide

RedactAI is built with standard Python tools, making it easy to install locally, in virtual environments, or within Docker containers.

## Prerequisites
- Python 3.10, 3.11, or 3.12
- Git (for source installations)
- Docker & Docker Compose (optional, for enterprise deployments)

---

## 1. Local Python Installation

### Virtual Environment (Recommended)
We strongly recommend installing RedactAI in an isolated virtual environment.

```bash
python -m venv redactai-env
source redactai-env/bin/activate  # On Windows: redactai-env\Scripts\activate
```

### Installation from Source (Editable)
Clone the repository and install it in editable mode (`-e`) so any changes to the source code are immediately reflected.

```bash
git clone https://github.com/snahadhar18/Redact-AI.git
cd Redact-AI

# Install the base engine
pip install -e .

# Install the full enterprise gateway (FastAPI, Redis, ML detectors)
pip install -e ".[api,json,ai,scale]"
```

**Extras Available:**
- `api`: Installs FastAPI and Uvicorn for the REST gateway.
- `json`: Installs JSON streaming dependencies.
- `ai`: Installs `spacy` and `presidio` for ML-based NLP detection.
- `scale`: Installs `redis` and `kafka-python` for horizontal scaling.
- `dev`: Installs `pytest`, `ruff`, and `mypy` for local development.

---

## 2. Docker Installation

For production deployments, the cleanest approach is to use our pre-built Docker container.

### Building the Image
```bash
docker build -t redactai:latest --target runtime .
```

### Running the CLI via Docker
You can mount a local directory and use the RedactAI CLI inside the container:
```bash
docker run --rm -v $(pwd)/logs:/logs redactai:latest redactai-engine scrub /logs/input.log /logs/output.log
```

### Running the API Gateway via Docker
```bash
docker run -d --name redactai-gateway -p 8000:8000 redactai:latest redactai-gateway serve --host 0.0.0.0 --port 8000
```

---

## 3. Docker Compose (Enterprise Setup)

For a complete scalable setup featuring the RedactAI gateway, Redis (for distributed locking and caching), and potentially Kafka, use Docker Compose.

```bash
docker-compose up -d --build
```
This will bring up the API on `http://localhost:8000`.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'redactai'`
Ensure you have activated your virtual environment and run `pip install -e .` from the root directory. If you are developing locally without installing, you must set `PYTHONPATH=src`.

### SpaCy Model Errors (`en_core_web_sm` not found)
If you are using the AI/ML NLP detectors, you must download the spaCy models manually after installing the `ai` extra:
```bash
python -m spacy download en_core_web_sm
```

### Windows Signal Errors (`OSError: [WinError 87]`)
If you use `redactai-gateway stream` on Windows, you may encounter an OS Error related to signal handling if trying to pipe inside certain shells (like PowerShell ISE). Please use standard PowerShell or Git Bash.
