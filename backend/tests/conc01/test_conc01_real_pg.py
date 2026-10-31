"""CONC-01: concurrencia REAL (hilos + Postgres real) sobre classify_pending_messages.

Requiere CONC01_PG_DSN (Postgres local desechable). Datos 100% sintéticos.
Sin DSN las pruebas se omiten: nunca apuntar a producción.
"""
from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

import pytest

DSN = os.environ.get("CONC01_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONC01_PG_DSN no definido")
if DSN and any(h in DSN for h in ("supabase.co", "supabase.com", "pooler")):
    raise RuntimeError("CONC-01: prohibido usar una BD remota")

WS = "15c1e9b8-0000-4000-8000-000000000001"
ACC = "d493c747-0000-4000-8000-000000000001"


@pytest.fixture()
def env(monkeypatch):
    from tests.conc01.pgclient import PgClient

    admin = PgClient(DSN)
    admin.conn().execute((Path(__file__).parent / "schema.sql").read_text())
    admin.conn().execute("insert into communication_accounts values (%s,%s,'me@yahoo.com')", (ACC, WS))

    clients: list[PgClient] = []

    class Storage:
        def __init__(self):
            self.client = PgClient(DSN)
            self.client.hooks = list(env_state["hooks"])
            clients.append(self.client)

        def get_account(self, account_id):
            r = self.client.table("communication_accounts").select("*").eq("id", account_id).execute().data
            return r[0] if r else None

    env_state = {"hooks": [], "push": []}
    import app.services.oauth_storage as oauth_storage
    import app.services.push_service as push_service

    monkeypatch.setattr(oauth_storage, "OAuthStorage", Storage)
    monkeypatch.setenv("BRAIN_V1_ENABLED", "false")
    for name in dir(push_service):
        if name.startswith(("notify", "send")) and callable(getattr(push_service, name)):
            monkeypatch.setattr(push_service, name, lambda *a, _n=name, **k: env_state["push"].append(_n))
    env_state["admin"] = admin
    import app.services.safe_case_classifier as scc
    env_state["lease"] = lambda d: monkeypatch.setattr(scc, "CLAIM_LEASE", d)
    return env_state


def _seed(admin, n=50):
    ids = []
    for i in range(n):
        mid = str(uuid.uuid4())
        actionable = i % 2 == 0
        admin.conn().execute(
            "insert into communication_messages (id,account_id,thread_id,external_message_id,sender,recipients,subject,body_text,snippet,received_at,direction)"
            " values (%s,%s,%s,%s,%s,'[\"me@yahoo.com\"]',%s,%s,%s, now() - (%s || ' minutes')::interval,'inbound')",
            (mid, ACC, f"t{i}", f"yahoo:Inbox:{1000+i}",
             f"Cliente {i} <cliente{i}@empresa{i}.mx>" if actionable else f"Promo <news@tienda{i}.com>",
             f"Solicitud de cotización urgente pedido {i}" if actionable else f"Oferta especial {i} 50% descuento",
             "Favor de enviar la cotización hoy, tenemos pago pendiente." if actionable
             else "Descuentos de la semana. Para dejar de recibir, cancele su suscripción. unsubscribe",
             "cotización" if actionable else "promo", str(i)))
        ids.append(mid)
    return ids


def _run_parallel(n_workers, ids=None, limit=500):
    from app.services.safe_case_classifier import classify_pending_messages

    results, errors = [None] * n_workers, []
    gate = threading.Barrier(n_workers)

    def work(i):
        gate.wait()
        try:
            results[i] = classify_pending_messages(account_id=ACC, workspace_id=WS, limit=limit, message_ids=ids)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(n_workers)]
    [t.start() for t in ts]
    [t.join(60) for t in ts]
    return results, errors


def _invariants(admin):
    q = lambda s: admin.conn().execute(s).fetchone()  # noqa: E731
    return {
        "pending": q("select count(*) c from communication_messages where not case_processed")["c"],
        "dup_case_messages": q("select count(*) c from (select message_id from case_messages group by 1 having count(*)>1) x")["c"],
        "cases_without_evidence": q("select count(*) c from intelligent_cases ic where not exists (select 1 from case_messages cm where cm.case_id=ic.id)")["c"],
        "cases": q("select count(*) c from intelligent_cases")["c"],
        "case_messages": q("select count(*) c from case_messages")["c"],
        "dup_case_created": q("select count(*) c from (select message_id from case_events where event_type='case_created' group by 1 having count(*)>1) x")["c"],
        "review_but_linked": q("select count(*) c from communication_messages m join case_messages cm on cm.message_id=m.id where m.triage_category='review'")["c"],
        "push_log": q("select count(*) c from push_delivery_log")["c"],
    }


def _assert_clean(env, inv):
    assert env["push"] == [] and inv["push_log"] == 0, "push"
    assert inv["dup_case_messages"] == 0, inv
    assert inv["dup_case_created"] == 0, inv
    assert inv["cases_without_evidence"] == 0, inv
    assert inv["review_but_linked"] == 0, inv


def _pause_before_case_insert(n):
    """Hace que n trabajadores lleguen juntos a la inserción del caso (ventana de carrera real)."""
    b = threading.Barrier(n, timeout=5)

    def hook(table, op, payload):
        if table == "intelligent_cases" and op == "insert":
            try:
                b.wait()
            except threading.BrokenBarrierError:
                pass
    return hook


def test_two_workers_same_message(env):
    ids = _seed(env["admin"], 1)  # mensaje accionable
    env["hooks"].append(_pause_before_case_insert(2))
    results, errors = _run_parallel(2, ids=ids)
    assert not errors
    inv = _invariants(env["admin"])
    assert inv["pending"] == 0
    assert inv["cases"] == 1 and inv["case_messages"] == 1, inv
    _assert_clean(env, inv)
    assert sum(r["processed"] for r in results) == 1, results  # un único resultado por mensaje


def test_two_workers_same_50(env):
    ids = _seed(env["admin"], 50)
    results, errors = _run_parallel(2, ids=ids)
    assert not errors
    inv = _invariants(env["admin"])
    assert inv["pending"] == 0, inv
    assert inv["case_messages"] == inv["cases"] == 25, inv
    _assert_clean(env, inv)
    assert sum(r["processed"] for r in results) == 50, [r["processed"] for r in results]


def test_eight_workers_same_50_no_pause(env):
    ids = _seed(env["admin"], 50)
    results, errors = _run_parallel(8, ids=None)
    assert not errors
    inv = _invariants(env["admin"])
    assert inv["pending"] == 0 and inv["cases"] == 25 == inv["case_messages"], inv
    _assert_clean(env, inv)
    assert sum(r["processed"] for r in results) == 50


class Crash(BaseException):
    """Simula un proceso que muere (no lo captura `except Exception`)."""


def test_retry_after_interrupted_run(env):
    ids = _seed(env["admin"], 50)
    state = {"n": 0}

    def crash_after_link(table, op, payload):
        # Muere justo tras vincular el 3er caso, antes de marcar case_processed.
        if table == "case_participants" and op == "select":
            state["n"] += 1
            if state["n"] == 3:
                raise Crash()
    env["hooks"].append(crash_after_link)
    _, errors = _run_parallel(1, ids=ids)
    assert errors and isinstance(errors[0], Crash)
    env["hooks"].clear()
    # Antes de caducar la reclamación, otro trabajador NO toma el mensaje reclamado.
    r_early, _ = _run_parallel(1, ids=ids)
    assert r_early[0]["skipped_claimed"] >= 1
    import app.services.safe_case_classifier as scc
    from datetime import timedelta
    env["lease"](timedelta(seconds=-5))  # simula que pasó el tiempo de la reclamación
    results, errors = _run_parallel(1, ids=ids)  # reintento
    assert not errors
    inv = _invariants(env["admin"])
    assert inv["pending"] == 0, inv  # ningún pendiente atascado
    assert inv["cases"] == 25 == inv["case_messages"], inv
    _assert_clean(env, inv)


def test_failure_between_case_insert_and_link(env):
    ids = _seed(env["admin"], 1)
    state = {"failed": False}

    def fail_link_once(table, op, payload):
        if table == "case_messages" and op == "insert" and not state["failed"]:
            state["failed"] = True
            raise RuntimeError("fallo sintético de red entre caso y vínculo")
    env["hooks"].append(fail_link_once)
    r1, _ = _run_parallel(1, ids=ids)
    assert r1[0]["errors"] == 1  # error visible
    row = env["admin"].conn().execute("select case_processed, triage_category, triage_reason from communication_messages").fetchone()
    assert row["case_processed"] is False and row["triage_category"] == "retry_pending" and "fallo sintético" in row["triage_reason"]
    env["hooks"].clear()
    # El error debe ser recuperable: el mensaje sigue disponible para reintento
    r2, _ = _run_parallel(1, ids=ids)
    inv = _invariants(env["admin"])
    assert inv["pending"] == 0
    assert inv["cases"] == 1 == inv["case_messages"], inv
    _assert_clean(env, inv)


def test_second_failure_is_final_and_visible(env):
    ids = _seed(env["admin"], 1)

    def always_fail(table, op, payload):
        if table == "case_messages" and op == "insert":
            raise RuntimeError("fallo persistente")
    env["hooks"].append(always_fail)
    _run_parallel(1, ids=ids)
    r2, _ = _run_parallel(1, ids=ids)
    row = env["admin"].conn().execute("select case_processed, triage_category from communication_messages").fetchone()
    assert row["case_processed"] is True and row["triage_category"] == "review"  # sin bucle infinito
    inv = _invariants(env["admin"])
    assert inv["cases"] == 1  # el huérfano del 1er intento se reutilizó, no se duplicó
    assert env["push"] == []
