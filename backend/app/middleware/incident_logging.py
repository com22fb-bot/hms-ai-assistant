from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.system_incident_service import record_incident


class IncidentLoggingMiddleware(BaseHTTPMiddleware):
    """Asigna request ID y registra respuestas 5xx o excepciones no controladas."""

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = (
            request.headers.get("x-request-id")
            or uuid4().hex
        )

        try:
            response = await call_next(request)
        except Exception as error:
            record_incident(
                component="backend/api",
                event_type="unhandled_exception",
                summary=(
                    f"Excepción no controlada en "
                    f"{request.method} {request.url.path}."
                ),
                severity="high",
                technical_detail=error,
                request_id=request_id,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise

        response.headers["X-Request-ID"] = request_id

        if response.status_code >= 500:
            record_incident(
                component="backend/api",
                event_type="http_5xx",
                summary=(
                    f"La API respondió HTTP {response.status_code} "
                    f"en {request.method} {request.url.path}."
                ),
                severity=(
                    "high"
                    if response.status_code >= 502
                    else "medium"
                ),
                http_status=response.status_code,
                request_id=request_id,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                },
            )

        return response
