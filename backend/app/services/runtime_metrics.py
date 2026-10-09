"""Métricas del propio proceso (sin servicios externos).

Anillo en memoria con las últimas peticiones (ruta, duración, estado) y
contadores de seguridad. Se reinicia con cada despliegue.
"""

from __future__ import annotations

import os
import threading
import time
from collections import Counter, deque
from typing import Any

STARTED_AT = time.time()
_RING: deque[tuple[float, str, float, int]] = deque(maxlen=5000)
_COUNTERS: Counter[str] = Counter()
_LOCK = threading.Lock()


def record_request(route: str, duration_ms: float, status: int) -> None:
    with _LOCK:
        _RING.append((time.time(), route, duration_ms, status))
        _COUNTERS["requests_total"] += 1
        if status == 401:
            _COUNTERS["unauthorized_401"] += 1
        elif status == 429:
            _COUNTERS["rate_limited_429"] += 1
        elif status >= 500:
            _COUNTERS["errors_5xx"] += 1


def bump(name: str) -> None:
    with _LOCK:
        _COUNTERS[name] += 1


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(pct / 100 * (len(ordered) - 1)))))
    return round(ordered[index], 1)


def _memory_rss_mb() -> float | None:
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        return None
    return None


def snapshot() -> dict[str, Any]:
    with _LOCK:
        ring = list(_RING)
        counters = dict(_COUNTERS)
    now = time.time()
    last_day = [item for item in ring if item[0] >= now - 86400]
    durations = [item[2] for item in last_day]
    errors = sum(1 for item in last_day if item[3] >= 500)
    per_route: dict[str, list[float]] = {}
    for _, route, ms, _status in last_day:
        per_route.setdefault(route, []).append(ms)
    routes = sorted(
        (
            {
                "route": route,
                "count": len(values),
                "avg_ms": round(sum(values) / len(values), 1),
                "p95_ms": _percentile(values, 95),
            }
            for route, values in per_route.items()
        ),
        key=lambda row: row["count"],
        reverse=True,
    )[:8]
    cpu = os.times()
    uptime = max(now - STARTED_AT, 1.0)
    return {
        "uptime_seconds": int(uptime),
        "memory_rss_mb": _memory_rss_mb(),
        "cpu_percent_avg": round((cpu.user + cpu.system) / uptime * 100, 2),
        "sample_size": len(last_day),
        "p50_ms": _percentile(durations, 50),
        "p95_ms": _percentile(durations, 95),
        "error_rate_pct": round(errors / len(last_day) * 100, 2) if last_day else 0.0,
        "routes": routes,
        "counters": {
            "requests_total": counters.get("requests_total", 0),
            "unauthorized_401": counters.get("unauthorized_401", 0),
            "rate_limited_429": counters.get("rate_limited_429", 0),
            "rate_limit_blocks": counters.get("rate_limit_blocks", 0),
            "direct_access_403": counters.get("direct_access_403", 0),
            "errors_5xx": counters.get("errors_5xx", 0),
        },
    }
