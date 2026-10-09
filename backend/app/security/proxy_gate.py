"""Solo el Worker de Cloudflare (app/www/donexto.com) puede llamar al backend.

El Worker agrega ``x-donexto-proxy`` con el secreto ``HMS_PROXY_SECRET`` y la
IP real del visitante en ``x-donexto-client-ip``. Sin el secreto configurado
no se bloquea nada (modo compatible para desplegar por partes).

Las rutas a las que el navegador llega directo (callbacks de OAuth que los
proveedores redirigen al dominio de Railway, y el healthcheck) siguen abiertas.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

PROXY_HEADER = "x-donexto-proxy"
CLIENT_IP_HEADER = "x-donexto-client-ip"

# Navegaciones del navegador o del proveedor directo al dominio de Railway.
_DIRECT_OK_EXACT = {"/", "/health"}


def proxy_secret() -> str:
    return os.getenv("HMS_PROXY_SECRET", "").strip()


def request_via_proxy(request: Request) -> bool:
    secret = proxy_secret()
    if not secret:
        return False
    supplied = request.headers.get(PROXY_HEADER, "")
    return bool(supplied) and hmac.compare_digest(supplied, secret)


def direct_access_allowed(method: str, path: str) -> bool:
    path = path.rstrip("/") or "/"
    if path in _DIRECT_OK_EXACT:
        return True
    # GET bajo /auth/: callbacks y redirecciones de OAuth (protegidas por state).
    return method.upper() in {"GET", "HEAD"} and path.startswith("/auth/")


def client_ip(request: Request) -> str:
    """IP del visitante para el límite de intentos.

    Con el secreto del Worker: la IP que Cloudflare vio (no la inventa el
    cliente). Directo a Railway: el último valor de X-Forwarded-For, que lo
    agrega el borde de Railway; el primero lo puede escribir cualquiera.
    """
    if request_via_proxy(request):
        forwarded_ip = request.headers.get(CLIENT_IP_HEADER, "").strip()
        if forwarded_ip:
            return forwarded_ip[:80]
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [part.strip() for part in forwarded.split(",") if part.strip()]
    if parts:
        return parts[-1][:80]
    host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return str(host)[:80]


class ProxyGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if (
            proxy_secret()
            and request.method.upper() != "OPTIONS"
            and not request_via_proxy(request)
            and not direct_access_allowed(request.method, request.url.path)
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "status": "direct_access_blocked",
                        "message": "Usa https://app.donexto.com.",
                    }
                },
            )
        return await call_next(request)
