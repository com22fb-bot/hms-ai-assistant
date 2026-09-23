"""Frontend origins allowed to receive OAuth and CORS from Donexto."""

from __future__ import annotations

PRODUCTION_APP_ORIGIN = "https://app.donexto.com"

# Admin is served on the marketing host. Allow these only when production
# already trusts the product app, so a localhost-only env does not grow.
MARKETING_ADMIN_ORIGINS = (
    "https://www.donexto.com",
    "https://donexto.com",
)


def expand_frontend_origins(origins: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in origins:
        value = (item or "").strip().rstrip("/")
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    if PRODUCTION_APP_ORIGIN in seen:
        for extra in MARKETING_ADMIN_ORIGINS:
            if extra not in seen:
                seen.add(extra)
                cleaned.append(extra)
    return cleaned
