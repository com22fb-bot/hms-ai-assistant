#!/usr/bin/env python3
"""Guard anti-doble respaldo. Lee JSON de /actions/workflows/<wf>/runs por stdin.

Uso: backup_guard.py <event_name> <run_id>   -> imprime run=true|false
Solo los eventos 'schedule' (respaldo de GitHub) pueden saltarse; workflow_dispatch
(cron de Cloudflare o manual) siempre corre. Se salta si hoy (UTC) ya hay otra corrida
exitosa, en curso o en cola del MISMO workflow (diario y semanal son independientes).
"""
import json, sys


def should_run(event: str, run_id: int, payload: dict, today: str) -> bool:
    if event != "schedule":
        return True
    for r in payload.get("workflow_runs", []):
        if r.get("id") == run_id or not str(r.get("created_at", "")).startswith(today):
            continue
        if r.get("conclusion") == "success" or r.get("status") in ("in_progress", "queued", "waiting", "pending", "requested"):
            return False
    return True


if __name__ == "__main__":
    from datetime import datetime, timezone
    ev, rid = sys.argv[1], int(sys.argv[2])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("run=" + ("true" if should_run(ev, rid, json.load(sys.stdin), today) else "false"))
