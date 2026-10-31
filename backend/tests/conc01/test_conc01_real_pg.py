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

PGRST = os.environ.get("CONC01_PGRST_URL")  # PostgREST local opcional
if PGRST and not PGRST.startswith(("http://127.0.0.1", "http://localhost")):
    raise RuntimeError("CONC-01: PostgREST debe ser local")
TRUNCATE = ("truncate case_notifications, case_events, case_participants, case_messages, intelligent_cases,"
            " organizational_patterns, communication_messages, communication_accounts, push_delivery_log cascade")
needs_hooks = pytest.mark.skipif(bool(PGRST), reason="inyección de fallos solo con el adaptador")

WS = "15c1e9b8-0000-4000-8000-000000000001"
ACC = "d493c747-0000-4000-8000-000000000001"


@pytest.fixture()
def env(monkeypatch):
    from tests.conc01.pgclient import PgClient

    admin = PgClient(DSN)
    try:
        admin.conn().execute(TRUNCATE)
    except Exception:
        admin.conn().execute((Path(__file__).parent / "schema.sql").read_text())
        admin.conn().execute("grant usage on schema public to conc01_anon; grant all on all tables in schema public to conc01_anon; notify pgrst, 'reload schema'")
    admin.conn().execute("insert into communication_accounts values (%s,%s,'me@yahoo.com')", (ACC, WS))

    clients: list[PgClient] = []

    class Storage:
        def __init__(self):
            if PGRST:
                from postgrest import SyncPostgrestClient
                self.client = SyncPostgrestClient(PGRST)
            else:
                self.client = PgClient(DSN)
                self.client.hooks = list(env_state["hooks"])
                self.client.default_returning = env_state["default_returning"]
            clients.append(self.client)

        def get_account(self, account_id):
            r = self.client.table("communication_accounts").select("*").eq("id", account_id).execute().data
            return r[0] if r else None

    env_state = {"hooks": [], "push": [], "default_returning": "representation"}
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


def _api_client(env):
    import app.services.oauth_storage as oauth_storage
    return oauth_storage.OAuthStorage().client


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


@needs_hooks
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


@needs_hooks
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


@needs_hooks
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


# --- Hallazgo ASTRA sobre PR #214: confirmación de la reclamación -----------------

@pytest.mark.skipif(bool(PGRST), reason="modo minimal simulado solo en el adaptador")
def test_update_without_representation_returns_empty_data(env):
    """Reproduce data=[] de un UPDATE EXITOSO con return=minimal: el patrón anterior
    bool(response.data) lo leería como 'no reclamado' aunque la fila sí cambió."""
    from tests.conc01.pgclient import PgClient

    ids = _seed(env["admin"], 1)
    c = PgClient(DSN)
    c.default_returning = "minimal"
    r = c.table("communication_messages").update({"triage_category": "classifying"}).eq("id", ids[0]).execute()
    assert r.data == []  # éxito sin cuerpo
    row = env["admin"].conn().execute("select triage_category from communication_messages").fetchone()
    assert row["triage_category"] == "classifying"  # pero la fila SÍ se actualizó
    assert bool(r.data) is False  # => la lógica anterior habría fallado


def test_representation_is_refiltered_by_postgrest(env):
    """Hallazgo real (PostgREST 12.2.3): con return=representation y count=exact,
    un UPDATE EXITOSO con un filtro lógico or= sobre la columna que cambia devuelve
    data=[] y count=0 (PostgREST reaplica or= a las filas devueltas). El patrón bool(response.data) del commit d2d0848 nunca confirmaba."""
    ids = _seed(env["admin"], 1)
    client = _api_client(env)
    r = (client.table("communication_messages")
         .update({"triage_category": "classifying"}, returning="representation", count="exact")
         .eq("id", ids[0]).or_("triage_category.is.null,triage_category.neq.classifying").execute())
    assert r.data == [] and r.count == 0
    row = env["admin"].conn().execute("select triage_category from communication_messages").fetchone()
    assert row["triage_category"] == "classifying"  # la fila SÍ cambió


def test_claim_does_not_depend_on_update_body(env):
    """Aunque el cliente devuelva siempre data=[] (return=minimal), la reclamación se
    confirma por el testigo leído con SELECT."""
    from app.services.safe_case_classifier import _claim_message
    from tests.conc01.pgclient import PgClient

    ids = _seed(env["admin"], 1)
    c = PgClient(DSN)
    c.default_returning = "minimal"
    assert _claim_message(c, ids[0]) is True


def test_claim_confirmed_and_exclusive(env):
    """Con representación pedida: 1ª reclamación True y fila devuelta; 2ª False (count=0, data=[])."""
    from app.services.safe_case_classifier import _claim_message
    import app.services.oauth_storage as oauth_storage

    ids = _seed(env["admin"], 1)
    client = oauth_storage.OAuthStorage().client
    assert _claim_message(client, ids[0]) is True
    # dos reclamaciones simultáneas sobre el mismo mensaje: exactamente una gana
    env["admin"].conn().execute("update communication_messages set triage_category='unreviewed'")
    wins = []
    gate = threading.Barrier(8)
    def claim():
        c = oauth_storage.OAuthStorage().client
        gate.wait()
        wins.append(_claim_message(c, ids[0]))
    ts = [threading.Thread(target=claim) for _ in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert wins.count(True) == 1, wins
    assert _claim_message(client, ids[0]) is False  # ya reclamado y vigente
    row = env["admin"].conn().execute("select triage_category, case_processed from communication_messages").fetchone()
    assert row["triage_category"] == "classifying" and row["case_processed"] is False


def test_claim_expires_and_never_stays_classifying(env):
    """Un 'classifying' abandonado se recupera al vencer la reclamación (filtro or_ con timestamp citado)."""
    ids = _seed(env["admin"], 4)
    env["admin"].conn().execute(
        "update communication_messages set triage_category='classifying', triaged_at = now() - interval '11 minutes'")
    results, errors = _run_parallel(1, ids=None)
    assert not errors and results[0]["skipped_claimed"] == 0
    left = env["admin"].conn().execute(
        "select count(*) c from communication_messages where triage_category='classifying' or not case_processed").fetchone()["c"]
    assert left == 0
    _assert_clean(env, _invariants(env["admin"]))


def test_fresh_claim_is_respected(env):
    """Una reclamación vigente (2 min) de otro trabajador no se toma."""
    _seed(env["admin"], 2)
    env["admin"].conn().execute(
        "update communication_messages set triage_category='classifying', triaged_at = now() - interval '2 minutes'")
    results, _ = _run_parallel(1, ids=None)
    assert results[0]["skipped_claimed"] == 2 and results[0]["processed"] == 0


# ---------------------------------------------------------------------------
# R2: vencimiento del lease mientras el trabajador 1 sigue activo (fencing).
# Funciona igual con el adaptador y con PostgREST 12.2.3 real (sin hooks).
# ---------------------------------------------------------------------------
def _expiry_scenario(env, monkeypatch, module, attr, actionable=True):
    from app.services.safe_case_classifier import classify_pending_messages

    ids = _seed(env["admin"], 2)
    target = [ids[0] if actionable else ids[1]]
    reached, release = threading.Event(), threading.Event()
    original = getattr(module, attr)

    def paused(*a, **k):
        if threading.current_thread().name == "w1" and not reached.is_set():
            reached.set()
            assert release.wait(30)
        return original(*a, **k)

    monkeypatch.setattr(module, attr, paused)
    out = {}

    def w1():
        out["w1"] = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=target)

    t = threading.Thread(target=w1, name="w1")
    t.start()
    assert reached.wait(30), "w1 no llegó al punto de pausa"
    tok1 = env["admin"].conn().execute(
        "select triage_reason from communication_messages where id=%s", (target[0],)).fetchone()["triage_reason"]
    assert tok1.startswith("classifying:")
    # el lease de w1 vence (simulado: 11 min atrás) y w2 recupera el mensaje
    env["admin"].conn().execute(
        "update communication_messages set triaged_at = now() - interval '11 minutes' where id=%s", (target[0],))
    out["w2"] = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=target)
    after_w2 = env["admin"].conn().execute(
        "select triage_category, triage_reason, triaged_at, processed_at, case_processed from communication_messages where id=%s",
        (target[0],)).fetchone()
    snap = _invariants(env["admin"])
    release.set()
    t.join(30)
    assert not t.is_alive()
    final = env["admin"].conn().execute(
        "select triage_category, triage_reason, triaged_at, processed_at, case_processed from communication_messages where id=%s",
        (target[0],)).fetchone()
    inv = _invariants(env["admin"])
    # w2 completó; w1 se retiró sin escribir
    assert out["w2"]["processed"] == 1 and out["w2"]["errors"] == 0, out["w2"]
    assert out["w1"]["processed"] == 0 and out["w1"]["lost_claims"] == 1 and out["w1"]["errors"] == 0, out["w1"]
    assert final == after_w2, "w1 escribió sin propiedad"
    assert {k: inv[k] for k in ("cases", "case_messages")} == {k: snap[k] for k in ("cases", "case_messages")}
    assert final["case_processed"] is True and not str(final["triage_reason"]).startswith("classifying:")
    exp = 1 if actionable else 0
    assert inv["cases"] == exp and inv["case_messages"] == exp, inv
    _assert_clean(env, inv)


def test_r2_lease_expires_before_case_insert(env, monkeypatch):
    import app.services.safe_case_classifier as scc
    _expiry_scenario(env, monkeypatch, scc, "classify_message")


def test_r2_lease_expires_after_link_before_final_mark(env, monkeypatch):
    import app.services.case_engine as ce
    _expiry_scenario(env, monkeypatch, ce, "_update_learning")


def test_r2_lease_expires_before_mark_without_case(env, monkeypatch):
    import app.services.safe_case_classifier as scc
    _expiry_scenario(env, monkeypatch, scc, "classify_message", actionable=False)
