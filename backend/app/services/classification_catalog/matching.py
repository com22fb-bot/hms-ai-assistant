from __future__ import annotations

from email.utils import getaddresses
from typing import Any


MARKETING_LOCAL_PARTS = (
    "newsletter",
    "newsletters",
    "marketing",
    "promo",
    "promos",
    "promocion",
    "promociones",
    "ofertas",
    "oferta",
    "offers",
    "deals",
    "campaign",
    "campaigns",
    "publicidad",
    "advertise",
    "ads",
    "digest",
    "info-comercial",
)


def sender_email(sender: str | None) -> str:
    values = getaddresses([sender or ""])
    if not values:
        return ""
    return values[0][1].strip().lower()


def sender_local_part(sender: str | None) -> str:
    email = sender_email(sender)
    if "@" not in email:
        return ""
    return email.split("@", 1)[0]


def sender_domain(sender: str | None) -> str:
    email = sender_email(sender)
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].strip().rstrip(".").lower()


def domain_suffix_in(domain: str, listed: str) -> bool:
    """Match registrable domain only. Never substring.

    mail.x.com → x.com  ✓
    citibanamex.com → x.com  ✗
    banamex.com → amex.com  ✗
    """
    host = (domain or "").strip().rstrip(".").lower()
    needle = (listed or "").strip().rstrip(".").lower()
    if not host or not needle:
        return False
    return host == needle or host.endswith("." + needle)


def match_listed_domain(
    domain: str,
    directory: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    host = (domain or "").strip().rstrip(".").lower()
    if not host or not directory:
        return None
    labels = host.split(".")
    for index in range(0, max(len(labels) - 1, 1)):
        candidate = ".".join(labels[index:])
        meta = directory.get(candidate)
        if meta is not None:
            return candidate, meta
    return None


def is_marketing_local_part(sender: str | None) -> bool:
    local = sender_local_part(sender)
    if not local:
        return False
    compact = local.replace(".", "-").replace("_", "-")
    return any(
        marker == compact
        or compact.startswith(marker + "-")
        or compact.endswith("-" + marker)
        or f"-{marker}-" in compact
        for marker in MARKETING_LOCAL_PARTS
    )
