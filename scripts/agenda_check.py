"""Checklist diario del respaldo: verifica la Agenda de herramientas y pagos por vencer.

Sin red ni secretos: evalúa la configuración (tools_agenda.py) contra la fecha de hoy.
Imprime el resultado (queda en el log del run) y escribe `status=`/`summary=` para GITHUB_OUTPUT.
Sale 0 siempre; el workflow decide alertar si status es medium/critical.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.services.tools_agenda import build_agenda  # noqa: E402

today = (datetime.now(timezone.utc) - timedelta(hours=6)).date()  # fecha CDMX
agenda = build_agenda(today)
names = {"low": "VERDE", "medium": "AMARILLO", "critical": "ROJO"}
lines = []
for row in agenda["rows"]:
    for d in row["dates"]:
        lines.append(f"{names[d['severity']]:8} {row['name']}: {d['label']} {d['on']} ({d['days']} d)")
print(f"Agenda {today} · estado {names[agenda['status']]} · TC {agenda['fx']['source']} {agenda['fx']['date']}: {agenda['fx']['usd_mxn']}")
print("\n".join(lines))
bad = [ln for ln in lines if not ln.startswith("VERDE")]
summary = "; ".join(x.strip() for x in bad) or "todo en verde"
out = os.getenv("GITHUB_OUTPUT")
if out:
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(f"status={agenda['status']}\nsummary={summary}\n")
