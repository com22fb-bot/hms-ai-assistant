"""Evalúa el cerebro con el corpus etiquetado usando el pipeline real.

Camino: safe_case_classifier.classify_pending_messages → (flag ON) brain_v1.engine /
(flag OFF) case_engine.process_message, sobre tests/fake_supabase.FakeSupabase.

Uso:
  python scripts/eval_brain.py --flag off            # línea base
  python scripts/eval_brain.py --flag on --check     # criterios de aceptación (sale 1 si falla)
  python scripts/eval_brain.py --flag both --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CORPUS = ROOT / "tests" / "brain_corpus" / "corpus.jsonl"
MX = ZoneInfo("America/Mexico_City")
W, A = "ws-eval", "acc-eval"
NOISE = {"social", "promotional", "informational", "automated"}
TRIAGE_MAP = {"action_required": "accion", "notice": "aviso", "waiting_external": "aviso", "review": "revision",
              "informational": "info", "automated": "info", "social": "social", "promotional": "promo"}
STATUS_ES = {"new": "pendiente", "analyzing": "pendiente", "in_progress": "en seguimiento", "delegated": "en seguimiento",
             "waiting_internal": "pendiente", "waiting_external": "esperando a otro", "scheduled": "programado",
             "resolved": "resuelto", "closed": "resuelto", "no_action": "sin acción", "needs_review": "requiere revisión"}
CLOSED = {"resolved", "closed", "archived", "no_action"}
THRESHOLDS = {"protected_lost": 0, "wrong_merges": 0, "invented_dates": 0, "date_accuracy": 0.95,
              "false_pending_rate": 0.05, "missing_case_rate": 0.05}


def load_corpus() -> list[dict]:
    return [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_pipeline(corpus: list[dict], flag: bool) -> dict:
    os.environ["BRAIN_V1_ENABLED"] = "true" if flag else "false"
    from tests.fake_supabase import FakeSupabase, _Query

    if not hasattr(_Query, "gte"):
        _Query.gte = lambda self, *_a: self  # type: ignore[attr-defined]
        _Query.lte = lambda self, *_a: self  # type: ignore[attr-defined]
    db = FakeSupabase({
        "communication_accounts": [{"id": A, "workspace_id": W, "provider": "gmail", "address": "usuario@correo.example"}],
        "workspace_members": [{"workspace_id": W, "user_id": "u-eval", "role": "owner"}],
        "communication_messages": [], "intelligent_cases": [], "case_messages": [], "case_events": [],
        "case_participants": [], "learning_patterns": [], "organizational_patterns": [],
    })
    db.auth = SimpleNamespace(admin=SimpleNamespace(get_user_by_id=lambda uid: SimpleNamespace(
        user=SimpleNamespace(app_metadata={"donexto_verified": True}))))
    for item in corpus:
        db.tables["communication_messages"].append({
            "id": item["id"], "thread_id": item["thread_id"], "account_id": A, "external_message_id": item["id"],
            "sender": item["sender"], "recipients": [{"email": "usuario@correo.example"}], "cc": [], "bcc": [],
            "subject": item["subject"], "body_text": item["body_text"], "snippet": item["body_text"][:200],
            "received_at": item["received_at"], "labels": item["labels"], "is_unread": True, "direction": "inbound",
            "case_processed": False, "ai_processed": False,
        })

    class Storage:
        client = db

        def get_account(self, _):
            return {"id": A, "workspace_id": W}

    import app.database.supabase as supabase_module

    supabase_module.get_supabase_client = lambda *a, **k: db  # nunca toca un Supabase real
    import app.services.oauth_storage as oauth_storage

    original = oauth_storage.OAuthStorage
    oauth_storage.OAuthStorage = lambda *a, **k: Storage()  # type: ignore[assignment]
    try:
        from app.services.safe_case_classifier import classify_pending_messages

        started = datetime.now()
        summary = classify_pending_messages(account_id=A, workspace_id=W, limit=500)
        elapsed = (datetime.now() - started).total_seconds()
    finally:
        oauth_storage.OAuthStorage = original
    return {"db": db, "summary": summary, "elapsed_s": elapsed}


def _local(value: str | None, with_time: bool) -> str | None:
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(MX)
    return dt.strftime("%Y-%m-%dT%H:%M" if with_time else "%Y-%m-%d")


def evaluate(corpus: list[dict], run: dict, flag: bool) -> dict:
    from app.services.brain_v1.protected import protected_type
    from app.services.import_categories import skip_message

    os.environ["BRAIN_V1_ENABLED"] = "true" if flag else "false"
    db = run["db"]
    msgs = {m["id"]: m for m in db.tables["communication_messages"]}
    cases = {c["id"]: c for c in db.tables["intelligent_cases"]}
    msg_case = {cm["message_id"]: cm["case_id"] for cm in db.tables["case_messages"]}
    events = db.tables["case_events"]
    by_id = {c["id"]: c for c in corpus}

    pred_cases: dict[str, list[str]] = defaultdict(list)
    for mid, cid in msg_case.items():
        pred_cases[cid].append(mid)
    exp_keys: dict[str, list[str]] = defaultdict(list)
    for item in corpus:
        if item["label"]["case_key"]:
            exp_keys[item["label"]["case_key"]].append(item["id"])

    wrong_merges = []
    correct_pred = 0
    for cid, mids in pred_cases.items():
        keys = {by_id[m]["label"]["case_key"] for m in mids if by_id[m]["label"]["case_key"]}
        if len(keys) > 1:
            wrong_merges.append({"case": cid[:8], "keys": sorted(keys)})
        elif len(keys) == 1:
            correct_pred += 1
    key_to_cases: dict[str, set[str]] = {k: {msg_case[m] for m in v if m in msg_case} for k, v in exp_keys.items()}
    duplicates = {k: len(v) for k, v in key_to_cases.items() if len(v) > 1}
    missing = sorted(k for k, v in key_to_cases.items() if not v)
    no_case_expected = [c for c in corpus if not c["label"]["crea_caso"]]
    false_pending = [c["id"] for c in no_case_expected
                     if c["id"] in msg_case and cases[msg_case[c["id"]]]["status"] not in CLOSED]

    date_checks = date_ok = invented = 0
    date_rows = []
    status_ok = priority_ok = 0
    for key, mids in exp_keys.items():
        label = by_id[mids[0]]["label"]
        cids = key_to_cases.get(key) or set()
        if not cids:
            continue
        case = cases[sorted(cids)[0]]
        meta = case.get("metadata") or {}
        exp_ev = label["event_at"]
        got_due = _local(case.get("due_at"), False)
        got_ev = _local(case.get("event_at") or meta.get("event_at"), bool(exp_ev and "T" in exp_ev))
        for name, exp, got in (("due_at", label["due_at"], got_due), ("event_at", exp_ev, got_ev)):
            date_checks += 1
            ok = exp == got
            date_ok += ok
            if got and not exp:
                invented += 1
            if not ok:
                date_rows.append({"key": key, "campo": name, "esperado": exp, "obtenido": got})
        status_ok += STATUS_ES.get(case["status"], case["status"]) == label["status"]
        from app.services.brain_v1.engine import PRIORITY_LEVEL

        priority_ok += PRIORITY_LEVEL.get(case["priority"], "?") == label["priority"]

    protected_lost, protected_lost_headers = [], []
    exclusion = ["social", "promos"]
    for item in corpus:
        prot = item["label"]["protected"]
        if not prot:
            continue
        m = msgs[item["id"]]
        lost = (m.get("triage_category") in NOISE and item["id"] not in msg_case) or skip_message(
            exclusion, item["sender"], item["subject"], item["labels"])
        if lost:
            protected_lost.append(item["id"])
        h = item["solo_cabeceras"]
        if protected_type(h["from"], h["subject"], None, {"list-unsubscribe": h.get("list-unsubscribe") or ""}) is None:
            protected_lost_headers.append(item["id"])

    # C5b: pagos de otro remitente o sin folio → "posible pago, confirmar", nunca resuelto.
    possible_expected = [c for c in corpus if c["label"].get("posible_pago")]
    possible_ok = 0
    auto_closed_wrong = 0
    for item in possible_expected:
        case = cases.get(msg_case.get(item["id"]))
        if case and case["status"] not in CLOSED and (case.get("metadata") or {}).get("payment_status") == "possible":
            possible_ok += 1
        if case and case["status"] in CLOSED:
            auto_closed_wrong += 1
    triage_ok = sum(TRIAGE_MAP.get(msgs[c["id"]].get("triage_category"), "?") == c["label"]["triage"] for c in corpus)
    n_keys = len(exp_keys)
    covered = n_keys - len(missing)
    metrics = {
        "flag": "ON" if flag else "OFF", "emails": len(corpus), "expected_cases": n_keys,
        "predicted_cases": len(pred_cases), "case_precision": round(correct_pred / max(len(pred_cases), 1), 3),
        "case_recall": round(covered / max(n_keys, 1), 3),
        "missing_case_rate": round(len(missing) / max(n_keys, 1), 3), "missing_cases": missing,
        "false_pending": len(false_pending), "false_pending_rate": round(len(false_pending) / max(len(no_case_expected), 1), 3),
        "false_pending_ids": false_pending, "duplicates": len(duplicates), "duplicate_keys": duplicates,
        "wrong_merges": len(wrong_merges), "wrong_merge_detail": wrong_merges,
        "date_accuracy": round(date_ok / max(date_checks, 1), 3), "invented_dates": invented, "date_errors": date_rows,
        "protected_lost": len(protected_lost), "protected_lost_ids": protected_lost,
        "protected_lost_headers_only": len(protected_lost_headers), "protected_lost_headers_only_ids": protected_lost_headers,
        "status_accuracy": round(status_ok / max(covered, 1), 3), "priority_accuracy": round(priority_ok / max(covered, 1), 3),
        "triage_accuracy": round(triage_ok / len(corpus), 3), "errors": run["summary"].get("errors"),
        "elapsed_s": round(run["elapsed_s"], 3),
        "possible_payment_ok": f"{possible_ok}/{len(possible_expected)}", "cross_sender_auto_closed": auto_closed_wrong,
    }
    metrics["partd"] = part_d(corpus, msgs, cases, msg_case, events, metrics)
    return metrics


def part_d(corpus, msgs, cases, msg_case, events, metrics) -> list[dict]:
    from app.services.import_categories import skip_message

    def case_of(mid):
        return cases.get(msg_case.get(mid))

    def due(mid):
        c = case_of(mid)
        return _local(c.get("due_at"), False) if c else None

    def ev(mid):
        c = case_of(mid)
        return _local((c or {}).get("event_at") or ((c or {}).get("metadata") or {}).get("event_at"), True) if c else None

    def conf(mid):
        m = msgs[mid]
        return m.get("brain_confidence")

    f1 = case_of("f1")
    vt_cases = {msg_case.get(f"vt{i}") for i in range(3)}
    rows = [
        ("D1 Factura con vencimiento", "caso accionable, due 2026-10-30", f"caso={'sí' if f1 else 'no'}, due={due('f1')}", bool(f1) and due("f1") == "2026-10-30"),
        ("D2 Recordatorio de la factura", "mismo caso, sin duplicar", f"mismo caso={msg_case.get('f2') == msg_case.get('f1') and bool(f1)}", bool(f1) and msg_case.get("f2") == msg_case.get("f1")),
        ("D3 Confirmación de pago", "resuelve el caso con evento payment_confirmed", f"estado={(f1 or {}).get('status')}, evento={any(e.get('event_type') == 'payment_confirmed' and e.get('message_id') == 'f3' for e in events)}",
         bool(f1) and f1["status"] == "resolved" and any(e.get("event_type") == "payment_confirmed" and e.get("message_id") == "f3" for e in events)),
        ("D4 Dos compras distintas, mismo importe", "dos casos", f"casos distintos={msg_case.get('c1') != msg_case.get('c2')}", bool(msg_case.get("c1")) and bool(msg_case.get("c2")) and msg_case.get("c1") != msg_case.get("c2")),
        ("D5 Promoción", "sin pendiente", f"triage={msgs['p1'].get('triage_category')}, caso={'p1' in msg_case}", "p1" not in msg_case),
        ("D6 Notificación social", "sin pendiente", f"triage={msgs['s1'].get('triage_category')}, caso={'s1' in msg_case}", "s1" not in msg_case),
        ("D7 Código/inicio de sesión en red social", "no se pierde (ni con 'social' excluido)",
         f"triage={msgs['s2'].get('triage_category')}, saltado con social excluido={skip_message(['social'], 'security@mail.instagram.com', msgs['s2']['subject'])}",
         msgs["s2"].get("triage_category") not in NOISE and not skip_message(["social"], "security@mail.instagram.com", msgs["s2"]["subject"])),
        ("D8 15 verificaciones de Donexto (verificado)", "agrupadas; sin pendiente",
         f"casos={len({msg_case.get(f'v{i}') for i in range(15)} - {None})}; tercero no verificado: 3 correos → {len(vt_cases - {None})} caso(s)",
         all(f"v{i}" not in msg_case for i in range(15)) and len(vt_cases - {None}) == 1 and None not in vt_cases),
        ("D9 Cita médica confirmada", "compromiso programado 2026-10-20T10:00", f"estado={(case_of('m1') or {}).get('status')}, event={ev('m1')}",
         bool(case_of("m1")) and ev("m1") == "2026-10-20T10:00" and case_of("m1")["status"] == "scheduled"),
        ("D10 'Paga cuanto antes' sin fecha", "pendiente sin fecha inventada", f"caso={'sí' if case_of('x1') else 'no'}, due={due('x1')}", bool(case_of("x1")) and due("x1") is None),
        ("D11 Correo ambiguo", "requiere revisión, confianza < 0.5", f"triage={msgs['a1'].get('triage_category')}, confianza={conf('a1')}",
         msgs["a1"].get("triage_category") == "review" and conf("a1") is not None and conf("a1") < 0.5),
        ("D12 Documentos 'el próximo viernes' (lun 12-oct)", "due 2026-10-16 CDMX", f"due={due('d1')}", due("d1") == "2026-10-16"),
    ]
    return [{"caso": r[0], "esperado": r[1], "obtenido": r[2], "pasa": bool(r[3])} for r in rows]


def check(metrics: dict) -> list[str]:
    failures = []
    if metrics["protected_lost"] > THRESHOLDS["protected_lost"]:
        failures.append("protected_lost")
    if metrics["wrong_merges"] > THRESHOLDS["wrong_merges"]:
        failures.append("wrong_merges")
    if metrics["invented_dates"] > THRESHOLDS["invented_dates"]:
        failures.append("invented_dates")
    if metrics["date_accuracy"] < THRESHOLDS["date_accuracy"]:
        failures.append("date_accuracy")
    if metrics["false_pending_rate"] > THRESHOLDS["false_pending_rate"]:
        failures.append("false_pending_rate")
    if metrics["missing_case_rate"] > THRESHOLDS["missing_case_rate"]:
        failures.append("missing_case_rate")
    if metrics["cross_sender_auto_closed"]:
        failures.append("cross_sender_auto_closed")
    if metrics["possible_payment_ok"].split("/")[0] != metrics["possible_payment_ok"].split("/")[1]:
        failures.append("possible_payment")
    if not all(row["pasa"] for row in metrics["partd"]):
        failures.append("partd")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flag", choices=["on", "off", "both"], default="both")
    parser.add_argument("--check", action="store_true", help="aplica criterios de aceptación a la corrida ON")
    parser.add_argument("--json", help="guarda las métricas en este archivo")
    args = parser.parse_args()
    corpus = load_corpus()
    results = []
    for flag in ([False, True] if args.flag == "both" else [args.flag == "on"]):
        results.append(evaluate(corpus, run_pipeline(corpus, flag), flag))
    keys = ["emails", "expected_cases", "predicted_cases", "case_precision", "case_recall", "missing_case_rate",
            "false_pending", "false_pending_rate", "duplicates", "wrong_merges", "date_accuracy", "invented_dates",
            "protected_lost", "protected_lost_headers_only", "status_accuracy", "priority_accuracy", "triage_accuracy", "possible_payment_ok", "cross_sender_auto_closed", "errors"]
    print("métrica | " + " | ".join(f"flag {r['flag']}" for r in results))
    for key in keys:
        print(f"{key} | " + " | ".join(str(r[key]) for r in results))
    for r in results:
        passed = sum(row["pasa"] for row in r["partd"])
        print(f"\nParte D (flag {r['flag']}): {passed}/12")
        for row in r["partd"]:
            print(f"  {'SÍ' if row['pasa'] else 'NO'} | {row['caso']} | {row['esperado']} | {row['obtenido']}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if args.check:
        on = next((r for r in results if r["flag"] == "ON"), None)
        failures = check(on) if on else ["no se corrió con flag ON"]
        print("\nAceptación:", "OK" if not failures else "FALLA " + ", ".join(failures))
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
