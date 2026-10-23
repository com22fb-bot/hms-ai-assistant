#!/usr/bin/env python3
"""Guard anti-doble respaldo (diario y semanal, cada uno sobre SU workflow).

Uso en Actions:  backup_guard.py <workflow.yml> <event_name> <run_id> <origen>
Imprime run=true|false (para $GITHUB_OUTPUT).

Origen persistente y verificable: el workflow fija `run-name: "... [origen=<x>]"` y la API lo
devuelve como `display_title` (no se depende de que la API devuelva los inputs).
  x = schedule (evento schedule) | cf-cron (dispatch del Worker) | manual (dispatch humano).
Corridas viejas sin etiqueta: event=schedule -> schedule; cualquier otra -> manual.

Reglas:
- Una corrida MANUAL siempre corre y NUNCA bloquea a una automática (un manual de prueba no
  puede hacer que se salte el primer respaldo automático del día).
- Una corrida AUTOMÁTICA (schedule o cf-cron) se salta cuando hoy (UTC) existe otra corrida
  AUTOMÁTICA ANTERIOR (id menor) del mismo workflow que:
    a) está en vuelo (queued/waiting/pending/requested/in_progress), o
    b) terminó success Y su job "backup" realmente corrió (no fue saltado).
- Solo corridas anteriores bloquean: dos corridas en cola nunca se bloquean mutuamente
  (evita que ambas se salten). La concurrencia del workflow serializa, así que el guard de la
  segunda se evalúa cuando la primera ya terminó (re-chequeo implícito).
- Lista paginada (gh api --paginate, created>=día UTC). Si la API falla => run=true
  (fallar hacia respaldar: un doble respaldo es inocuo, uno faltante no).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Callable, Iterable

IN_FLIGHT = {"queued", "waiting", "pending", "requested", "in_progress"}
AUTOMATIC = {"schedule", "cf-cron"}
_TAG = re.compile(r"\[origen=([a-z-]+)\]")


def origin_of(run: dict) -> str:
    m = _TAG.search(str(run.get("display_title") or ""))
    if m:
        return m.group(1)
    return "schedule" if run.get("event") == "schedule" else "manual"


def current_origin(event: str, origin: str) -> str:
    if event == "schedule":
        return "schedule"
    return "cf-cron" if origin == "cf-cron" else "manual"


def backup_job_ran(jobs: list[dict]) -> bool:
    for j in jobs:
        if j.get("name") == "backup":
            return j.get("conclusion") == "success"
    return False


def should_run(event: str, origin: str, run_id: int, runs: Iterable[dict], today: str,
               jobs_of: Callable[[int], list[dict]]) -> bool:
    if current_origin(event, origin) not in AUTOMATIC:
        return True
    for r in runs:
        rid = int(r.get("id") or 0)
        if rid >= run_id or not str(r.get("created_at", "")).startswith(today):
            continue
        if origin_of(r) not in AUTOMATIC:
            continue  # un manual nunca bloquea a una automática
        if r.get("status") in IN_FLIGHT:
            return False
        if r.get("conclusion") == "success" and backup_job_ran(jobs_of(rid)):
            return False
    return True


def _gh_json_lines(path: str, jq: str) -> list[dict]:
    out = subprocess.run(["gh", "api", "--paginate", path, "--jq", jq],
                         check=True, capture_output=True, text=True, timeout=120).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def main() -> None:
    wf, event, run_id, origin = sys.argv[1], sys.argv[2], int(sys.argv[3]), (sys.argv[4] if len(sys.argv) > 4 else "")
    import os
    repo = os.environ["GITHUB_REPOSITORY"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        runs = _gh_json_lines(f"repos/{repo}/actions/workflows/{wf}/runs?created=%3E%3D{today}&per_page=100",
                              ".workflow_runs[]")
        jobs_of = lambda rid: _gh_json_lines(f"repos/{repo}/actions/runs/{rid}/jobs?per_page=100", ".jobs[]")
        ok = should_run(event, origin, run_id, runs, today, jobs_of)
    except Exception as e:  # noqa: BLE001
        print(f"guard: API falló ({type(e).__name__}); se respalda igual", file=sys.stderr)
        ok = True
    print("run=" + ("true" if ok else "false"))


if __name__ == "__main__":
    main()
