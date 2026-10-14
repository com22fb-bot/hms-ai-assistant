"""Evaluador de cobertura por categoría y por tipo de acción (lotes ciegos).

Uso: python scripts/eval_coverage.py <clave.csv> <salidas.json> [--run flag_on_con_cabeceras] [--json out.json]

La clave es un CSV con: case_id, expected_action, expected_area, expected_status, expected_priority, expected_date.
Las salidas son el JSON del runner (runs -> <corrida> -> messages -> {case_id: resultado}).
No modifica nada; solo lee. Los errores obligatorios se reportan aparte de la cobertura.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict

OPEN = {"new", "analyzing", "in_progress", "delegated", "waiting_internal", "waiting_external", "scheduled", "needs_review"}
HIDDEN = {"informational", "promotional", "social", "excluded"}


def predicted(out: dict) -> set[str]:
    """Acciones que la salida satisface (una salida puede cumplir varias, p. ej. caso en revisión)."""
    acts: set[str] = set()
    case, status, triage = out.get("case"), out.get("case_status"), out.get("triage")
    if case:
        acts.add("create_case")
        if (out.get("case_source_count") or 1) > 1:
            acts |= {"update_existing_case", "no_duplicate_case"}
        if status == "needs_review":
            acts.add("review")
    else:
        acts |= {"no_new_case", "no_duplicate_case"}
        if triage == "notice" or out.get("protected"):
            acts.add("create_notice")
        if triage == "review":
            acts.add("review")
        if triage in HIDDEN:
            acts.add("ignore")
    return acts


def mandatory_errors(row: dict, out: dict) -> list[str]:
    errs = []
    area, exp_date = row.get("expected_area"), (row.get("expected_date") or "").strip()
    if area == "security" and (out.get("triage") in HIDDEN or out.get("skipped_if_noise_excluded")):
        errs.append("seguridad_oculta")
    # Solo cuenta si el caso nació de este mensaje (un caso existente puede traer su propio vencimiento).
    if not exp_date and out.get("case_due") and (out.get("case_source_count") or 1) == 1:
        errs.append("fecha_inventada")
    if out.get("case_status") in {"resolved", "closed"} and row.get("expected_status") not in {"resolved", "closed"}:
        errs.append("resolucion_falsa")
    if out.get("case_priority") == "critical" and row.get("expected_priority") in {"normal", "low"}:
        errs.append("critica_sin_base")
    if out.get("triage") == "promotional" and row.get("expected_action") in {"create_case", "review"}:
        errs.append("obligacion_como_publicidad")
    return errs


def evaluate(key_rows: list[dict], outputs: dict) -> dict:
    by_area: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_action: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    misses, mandatory = [], []
    for row in key_rows:
        cid = row["case_id"]
        out = outputs.get(cid) or {}
        hit = row["expected_action"] in predicted(out)
        for bucket, k in ((by_area, row["expected_area"]), (by_action, row["expected_action"])):
            bucket[k][0] += 1
            bucket[k][1] += int(hit)
        if not hit:
            misses.append({"case_id": cid, "area": row["expected_area"], "esperado": row["expected_action"],
                           "obtenido": sorted(predicted(out)), "regla": out.get("rule")})
        for e in mandatory_errors(row, out):
            mandatory.append({"case_id": cid, "error": e, "regla": out.get("rule")})
    fmt = lambda b: {k: {"n": n, "aciertos": h, "cobertura": round(h / n, 3)} for k, (n, h) in sorted(b.items())}
    total = sum(n for n, _ in by_action.values())
    hits = sum(h for _, h in by_action.values())
    return {"total": total, "aciertos": hits, "cobertura": round(hits / total, 3) if total else None,
            "por_categoria": fmt(by_area), "por_accion": fmt(by_action), "fallos": misses, "errores_obligatorios": mandatory}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("outputs")
    ap.add_argument("--run", default="flag_on_con_cabeceras")
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.key, encoding="utf-8")))
    outs = json.load(open(a.outputs, encoding="utf-8"))["runs"][a.run]["messages"]
    res = evaluate(rows, outs)
    print(f"Corrida {a.run}: cobertura {res['aciertos']}/{res['total']} = {res['cobertura']}")
    for title, key in (("Por categoría", "por_categoria"), ("Por acción", "por_accion")):
        print(f"\n{title}:")
        for k, v in res[key].items():
            print(f"  {k:22s} {v['aciertos']:>3}/{v['n']:<3} {v['cobertura']:.0%}")
    print(f"\nErrores obligatorios: {len(res['errores_obligatorios'])}")
    for e in res["errores_obligatorios"]:
        print(f"  {e['case_id']}: {e['error']} ({e['regla']})")
    print(f"\nFallos de cobertura: {len(res['fallos'])}")
    for m in res["fallos"]:
        print(f"  {m['case_id']} [{m['area']}] esperado={m['esperado']} obtenido={m['obtenido']} regla={m['regla']}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 1 if res["errores_obligatorios"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
