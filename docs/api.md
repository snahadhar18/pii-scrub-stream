# REST API Reference

The RedactAI Gateway exposes a high-performance REST API powered by FastAPI.

## OpenAPI Specification
When the server is running, the interactive Swagger UI is available at `http://localhost:8000/docs`.

<div align="center">
  <img src="assets/screenshot_api.png" alt="OpenAPI Screenshot" width="800"/>
</div>

---

## Endpoints

### 1. `POST /scan`
Scans a single block of text and returns the redacted string along with detailed detection spans.

**Request Body:**
```json
{
  "text": "My phone number is 555-0199 and my email is test@example.com.",
  "detectors": ["email", "phone"],
  "redact": true,
  "mask": false
}
```

**Response (200 OK):**
```json
{
  "record_id": "req-1234",
  "original_length": 61,
  "redacted": "My phone number is [PHONE_REDACTED] and my email is [EMAIL_REDACTED].",
  "hit_count": 2,
  "labels": ["PHONE", "EMAIL"],
  "spans": [
    {
      "start": 19,
      "end": 27,
      "label": "PHONE",
      "value": "555-0199",
      "confidence": 0.9,
      "replacement": "[PHONE_REDACTED]"
    },
    {
      "start": 44,
      "end": 60,
      "label": "EMAIL",
      "value": "test@example.com",
      "confidence": 0.99,
      "replacement": "[EMAIL_REDACTED]"
    }
  ],
  "risk_score": 0.85
}
```

### 2. `POST /stream`
Accepts a JSON array of text records and streams back the redacted results asynchronously using Server-Sent Events (SSE) or Ndjson. Ideal for high-throughput batching.

**Request Body:**
```json
{
  "records": [
    {"id": "1", "text": "Hello alice@example.com"},
    {"id": "2", "text": "IP address 192.168.1.1"}
  ]
}
```

### 3. `POST /ingest`
Upload a CSV or JSON file via `multipart/form-data` to have it processed in the background.

**Response (202 Accepted):**
```json
{
  "job_id": "job-59284a",
  "status": "processing"
}
```

### 4. `GET /health`
Kubernetes readiness/liveness probe.

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "detectors_loaded": 10
}
```

### 5. `GET /metrics`
Returns Prometheus-compatible metrics for observability.

---

## Authentication
By default, the gateway ships **without** authentication. It is designed to be deployed behind a secure VPC boundary, an API Gateway (like Kong or AWS API Gateway), or a service mesh (like Istio) where TLS termination and OAuth2/JWT validation occurs.

## Error Codes
- **400 Bad Request:** Invalid JSON payload or missing required fields.
- **422 Unprocessable Entity:** Validation error (e.g., requesting a detector that isn't registered).
- **500 Internal Server Error:** Core engine failure.
