from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.services.runtime_metrics import record_request


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Mide duración y estado de cada petición (sin datos personales)."""

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            template = getattr(route, "path", None) or "(sin ruta)"
            record_request(
                f"{request.method} {template}",
                (time.perf_counter() - started) * 1000,
                status,
            )
