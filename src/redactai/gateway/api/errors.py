"""Centralized, structured error handling for the API.

Maps the library's exception hierarchy onto consistent HTTP responses using the
:class:`~redactai.gateway.api.schemas.ErrorResponse` envelope, so clients always get
a predictable shape regardless of where the failure originated.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from redactai.gateway.core.exceptions import (
    ConfigurationError,
    DetectorError,
    IngestionError,
    ProcessingError,
    RagGuardianError,
)

logger = logging.getLogger(__name__)

#: Map exception types to HTTP status codes. 422 is spelled as a literal to stay
#: compatible across Starlette versions that rename the constant.
_STATUS_MAP: dict[type[Exception], int] = {
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    IngestionError: 422,
    ProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DetectorError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _envelope(exc: Exception, code: int) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "type": "redactai.gateway_error",
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to ``app``."""

    @app.exception_handler(RagGuardianError)
    async def _handle_known(_request: Request, exc: RagGuardianError) -> JSONResponse:
        code = _STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        logger.warning("handled %s: %s", type(exc).__name__, exc)
        return _envelope(exc, code)

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "an unexpected error occurred",
                "type": "internal_error",
            },
        )


__all__ = ["register_error_handlers"]
