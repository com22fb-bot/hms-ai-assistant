from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.security.identity import (
    authenticate_request,
    reset_request_context,
    resolve_workspace_context,
    set_request_context,
)


_PROTECTED_PREFIXES = (
    "/identity",
    "/cases",
    "/messages",
    "/push",
    "/gmail",
    "/ai",
    "/dashboard",
    "/auth/google/start",
    "/auth/google/status",
    "/auth/google/disconnect",
    "/auth/yahoo",
    "/auth/microsoft",
)

_PUBLIC_PATHS = {
    "/auth/google/callback",
    "/auth/google/login",
    "/auth/yahoo/enter",
    "/auth/yahoo/login",
    "/auth/yahoo/callback",
    "/auth/microsoft/login",
    "/auth/microsoft/callback",
    "/auth/login/resolve",
}


class AuthenticationContextMiddleware(BaseHTTPMiddleware):
    """Validate Supabase Auth and establish the current HMS workspace."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    @staticmethod
    def _requires_identity(request: Request) -> bool:
        if request.method.upper() == "OPTIONS":
            return False

        path = request.url.path.rstrip("/") or "/"

        if path in _PUBLIC_PATHS:
            return False

        return any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in _PROTECTED_PREFIXES
        )

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if not self._requires_identity(request):
            return await call_next(request)

        context_token = None

        try:
            user = await run_in_threadpool(authenticate_request, request)
            context = await run_in_threadpool(
                resolve_workspace_context,
                request,
                user,
            )
            request.state.hms_context = context
            context_token = set_request_context(context)
            return await call_next(request)
        except HTTPException as error:
            return JSONResponse(
                status_code=error.status_code,
                content={"detail": error.detail},
                headers=error.headers,
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": {
                        "status": "identity_error",
                        "message": (
                            "No fue posible establecer el contexto seguro "
                            "de la cuenta Donexto."
                        ),
                    }
                },
            )
        finally:
            if context_token is not None:
                reset_request_context(context_token)
