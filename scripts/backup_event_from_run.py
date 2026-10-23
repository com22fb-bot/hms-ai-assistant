#!/usr/bin/env python3
"""Registra en la bitácora (/admin) el resultado de corridas de respaldo de GitHub Actions.

Uso:
  backup_event_from_run.py <run_id> [<run_id> ...]     # corridas concretas
  backup_event_from_run.py --backfill [N]              # últimas N de diario y semanal

Necesita: gh autenticado (GH_TOKEN en Actions), SUPABASE_URL, SUPABASE_SECRET_KEY.
Idempotente (external_id = gh-run-<id>). Nunca imprime secretos ni falla el job.
"""
import json, os, re, subprocess, sys, urllib.request
from datetime import datetime

KINDS = {"Donexto backup daily": "diario", "Donexto backup weekly": "semanal"}
SIZE_RE = re.compile(r"size[= ](\d+)")


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, timeout=120).stdout


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def guard_skipped(run: dict) -> bool:
    jobs = {j.get("name"): j.get("conclusion") for j in run.get("jobs") or []}
    return jobs.get("backup") == "skipped"


def event_for(run_id: str) -> dict | None:
    run = json.loads(gh("run", "view", run_id, "--json",
                        "databaseId,workflowName,conclusion,status,startedAt,updatedAt,url,jobs"))
    kind = KINDS.get(run["workflowName"])
    if not kind or run["status"] != "completed" or run["conclusion"] in ("cancelled", "skipped"):
        return None
    # Corrida de respaldo (schedule de GitHub) que el guard saltó porque el cron de
    # Cloudflare ya respaldó ese día: no es un respaldo, no se registra.
    if guard_skipped(run):
        return None
    ok = run["conclusion"] == "success"
    size = None
    try:
        sizes = [int(m) for m in SIZE_RE.findall(gh("run", "view", run_id, "--log"))]
        size = max(sizes) if sizes else None
    except Exception:  # noqa: BLE001
        pass
    duration = int((ts(run["updatedAt"]) - ts(run["startedAt"])).total_seconds())
    # Diario: head-object en R2 tras la subida. Semanal: sha256sum -c del objeto subido.
    verified = ok and size is not None
    mb = f"{size / 1048576:.1f} MB" if size else "tamaño desconocido"
    return {
        "occurred_at": run["startedAt"],
        "ended_at": run["updatedAt"],
        "source": "backup",
        "severity": "info" if ok else "grave",
        "title": f"Respaldo {kind}: {'ok' if ok else 'fallido'}",
        "detail": f"{mb} · {duration} s · {'verificado' if verified else 'sin verificar'}",
        "status": "resuelto",
        "created_by": "github-actions",
        "external_id": f"gh-run-{run['databaseId']}",
        "meta": {"kind": kind, "result": "ok" if ok else "fallido", "size_bytes": size,
                 "duration_s": duration, "verified": verified, "run_url": run["url"]},
    }


def post(rows: list[dict]) -> None:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key or not rows:
        print(f"bitácora: nada que registrar ({len(rows)} eventos, credenciales {'sí' if url and key else 'no'}).")
        return
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/admin_events?on_conflict=external_id",
        data=json.dumps(rows).encode(), method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"bitácora: {len(rows)} eventos de respaldo registrados (HTTP {r.status}).")
    except Exception as exc:  # noqa: BLE001
        print(f"bitácora: no se registró ({type(exc).__name__}).", file=sys.stderr)


def main() -> None:
    args = sys.argv[1:]
    ids: list[str] = []
    if args and args[0] == "--backfill":
        n = args[1] if len(args) > 1 else "50"
        for wf in ("backup-daily.yml", "backup-weekly.yml"):
            ids += [str(r["databaseId"]) for r in json.loads(gh("run", "list", "-w", wf, "-L", n, "--json", "databaseId"))]
    else:
        ids = args
    rows = []
    for rid in ids:
        try:
            ev = event_for(rid)
        except Exception as exc:  # noqa: BLE001
            print(f"run {rid}: omitido ({type(exc).__name__})", file=sys.stderr)
            continue
        if ev:
            rows.append(ev)
    post(rows)


if __name__ == "__main__":
    main()
