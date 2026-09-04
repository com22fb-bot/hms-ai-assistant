"""Lightweight in-process rate limiting for public auth endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

_hits: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def allow_request(
    key: str,
    *,
    max_requests: int = 30,
    window_seconds: int = 60,
) -> bool:
    now = time.monotonic()
    with _lock:
        recent = [stamp for stamp in _hits[key] if stamp > now - window_seconds]
        if len(recent) >= max_requests:
            _hits[key] = recent
            return False
        recent.append(now)
        _hits[key] = recent
        return True
