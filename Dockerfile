# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# RedactAI -- production multi-stage image.
#
# Stage 1 (builder): install the package and its API extras into an isolated
# virtualenv so the final image carries only runtime artifacts (no build tools,
# no caches). Stage 2 (runtime): copy the venv onto a slim base, run as a
# non-root user, and expose the FastAPI service.
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Create an isolated venv we can copy wholesale into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only what's needed to build the wheel first for better layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --upgrade pip && pip install ".[api,json]"

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    REDACTAI_API__HOST=0.0.0.0 \
    REDACTAI_API__PORT=8000 \
    REDACTAI_OBSERVABILITY__LOG_FORMAT=json

# Non-root runtime user.
RUN groupadd --system app && useradd --system --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER app

EXPOSE 8000

# Container-level health probe hits the API's /health endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# Run the ASGI app via uvicorn using the application factory.
CMD ["uvicorn", "redactai.gateway.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
