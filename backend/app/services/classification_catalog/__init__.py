from __future__ import annotations

from typing import Any

from app.services.classification_catalog.banks import BANKS
from app.services.classification_catalog.commerce import COMMERCE
from app.services.classification_catalog.matching import (
    is_marketing_local_part,
    match_listed_domain,
    sender_domain,
    sender_email,
)
from app.services.classification_catalog.social import SOCIAL
from app.services.classification_catalog.taxonomy import (
    N1_KEYS,
    N2_KEYS,
    N3_KEYS,
    SECURITY_NOTICE_TERMS,
    TRIAGE_CATALOG,
    TRIAGE_KEYS,
    VERTICALS,
)
from app.services.classification_catalog.travel import TRAVEL

__all__ = [
    "BANKS",
    "COMMERCE",
    "N1_KEYS",
    "N2_KEYS",
    "N3_KEYS",
    "SECURITY_NOTICE_TERMS",
    "SOCIAL",
    "TRAVEL",
    "TRIAGE_CATALOG",
    "TRIAGE_KEYS",
    "VERTICALS",
    "identify_sender",
    "is_marketing_local_part",
    "sender_domain",
    "sender_email",
]


def identify_sender(sender: str | None) -> dict[str, Any] | None:
    """Devuelve el vertical conocido del remitente, o None."""
    domain = sender_domain(sender)
    if not domain:
        return None
    for directory in (BANKS, COMMERCE, TRAVEL, SOCIAL):
        matched = match_listed_domain(domain, directory)
        if matched is None:
            continue
        listed, meta = matched
        return {
            "domain": listed,
            "host": domain,
            "email": sender_email(sender),
            **meta,
        }
    return None
