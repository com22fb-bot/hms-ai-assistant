"""Safe redirect targets for OAuth callbacks (open-redirect hardening)."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import settings

YAHOO_DEFAULT_RETURN = "https://app.donexto.com/"


def allowed_frontend_origins() -> set[str]:
    """Exact scheme://host[:port] origins permitted for post-OAuth redirects."""
    allowed: set[str] = set()
    for item in settings.frontend_origins:
        clean = (item or "").strip().rstrip("/")
        if not clean:
            continue
        try:
            parsed = urlparse(clean)
        except ValueError:
            continue
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            allowed.add(f"{parsed.scheme}://{parsed.netloc}".rstrip("/"))
    return allowed


# Only these paths may survive an OAuth return. Anything else collapses to /.
_SAFE_RETURN_PATHS = {"/", "/admin"}


def _safe_return_path(path: str) -> str:
    clean = path or "/"
    if len(clean) > 1 and clean.endswith("/"):
        clean = clean.rstrip("/") or "/"
    if clean not in _SAFE_RETURN_PATHS:
        return "/"
    return clean


def sanitize_return_to(value: str | None) -> str:
    """Return a safe frontend URL, never an attacker-controlled host.

    `/` and `/admin` are kept. Other paths on an allowed origin become `/`.
    """
    allowed = allowed_frontend_origins()
    if value:
        try:
            parsed = urlparse(value)
        except ValueError:
            parsed = None
        if parsed and parsed.scheme in {"http", "https"} and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            if origin in allowed:
                path = _safe_return_path(parsed.path or "/")
                if path == "/":
                    return origin + "/"
                return origin + path
    for origin in sorted(allowed):
        if origin.startswith("https://") and "donexto.com" in origin.lower():
            return origin + "/"
    if allowed:
        return sorted(allowed)[0] + "/"
    return YAHOO_DEFAULT_RETURN
