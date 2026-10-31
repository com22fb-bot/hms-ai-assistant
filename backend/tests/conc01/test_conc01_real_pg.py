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

ROOT = Path(__file__).resolve().parents[3]
RPC_SQL = ROOT / "supabase/migrations/20261031_001_conc01_commit_message.sql"
RPC_ROLLBACK = ROOT / "supabase/rollbacks/20261031_001_conc01_commit_message_rollback.sql"
WS = "15c1e9b8-0000-4000-8000-000000000001"
ACC = "d493c747-0000-4000-8000-000000000001"


@pytest.fixture()
def env(monkeypatch):
    from tests.conc01.pgclient import PgClient

    admin = PgClient(DSN)
    # Esquema réplica de producción (estructura) + migración propuesta, SOLO en esta BD local.
    admin.conn().execute((Path(__file__).parent / "schema.sql").read_text())
    admin.conn().execute("drop function if exists conc01_commit_message(uuid,text,jsonb)")
    admin.conn().execute(RPC_SQL.read_text())
    # conc01_anon = rol de PostgREST local; como service_role en producción: BYPASSRLS.
    admin.conn().execute("alter role conc01_anon bypassrls; grant usage on schema public to conc01_anon;"
                         " grant all on all tables in schema public to conc01_anon;"
                         " grant execute on function conc01_commit_message(uuid,uuid,uuid,text,jsonb) to conc01_anon;"
                         " drop table if exists conc01_fail cascade; create table conc01_fail (tbl text primary key);"
                         " drop function if exists conc01_test_gate() cascade;"
                         " grant all on conc01_fail to conc01_anon; notify pgrst, 'reload schema'")
    import time; time.sleep(0.4) if PGRST else None
    admin.conn().execute("insert into workspaces values (%s)", (WS,))
    admin.conn().execute("insert into communication_accounts (id, workspace_id, email) values (%s,%s,'me@yahoo.com')", (ACC, WS))

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


def _thread(admin, i):
    tid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"conc01-thread-{i}"))
    admin.conn().execute("insert into communication_threads values (%s) on conflict do nothing", (tid,))
    return tid


def _seed(admin, n=50):
    ids = []
    for i in range(n):
        mid = str(uuid.uuid4())
        actionable = i % 2 == 0
        admin.conn().execute(
            "insert into communication_messages (id,account_id,thread_id,external_message_id,sender,recipients,subject,body_text,snippet,received_at,direction)"
            " values (%s,%s,%s,%s,%s,'[\"me@yahoo.com\"]',%s,%s,%s, now() - (%s || ' minutes')::interval,'inbound')",
            (mid, ACC, _thread(admin, i), f"yahoo:Inbox:{1000+i}",
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
        "events": q("select count(*) c from case_events")["c"],
        "notifications": q("select count(*) c from case_notifications")["c"],
        "participants": q("select count(*) c from case_participants")["c"],
        "patterns": q("select count(*) c from organizational_patterns")["c"],
        "events_without_case": q("select count(*) c from case_events e where not exists (select 1 from intelligent_cases c where c.id=e.case_id)")["c"],
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
    assert inv["pending"] == 0, [r["error_details"] for r in results]
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
    assert inv["cases"] == 0  # R2: la transacción atómica no deja caso huérfano
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
    side = ("cases", "case_messages", "events", "notifications", "participants", "patterns")
    assert {k: inv[k] for k in side} == {k: snap[k] for k in side}, (snap, inv)  # 0 efectos de w1
    assert inv["events_without_case"] == 0
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


def test_r2_lease_lost_after_case_insert_before_event(env, monkeypatch):
    """TOCTOU de d09ff23: w1 ya validó y 'creó' el caso; pierde el lease antes del evento."""
    import app.services.case_engine as ce
    _expiry_scenario(env, monkeypatch, ce, "create_case_event")


def test_r2_lease_lost_right_before_atomic_commit(env, monkeypatch):
    """w1 terminó todo su trabajo y pierde el lease justo antes de la RPC: 0 escrituras."""
    import app.services.conc01_fenced_writes as fw
    _expiry_scenario(env, monkeypatch, fw, "commit_fenced")


BUSINESS_TABLES = ("intelligent_cases", "case_events", "case_notifications", "case_messages",
                   "case_participants", "organizational_patterns", "communication_messages")
GATE_SQL = """
create sequence if not exists conc01_fail_seq; grant usage, select, update on sequence conc01_fail_seq to conc01_anon;
create or replace function public.conc01_test_gate() returns trigger language plpgsql as $$
begin
  -- Fallo sintético UNA sola vez (la secuencia no se revierte con el rollback).
  if exists (select 1 from public.conc01_fail where tbl = tg_table_name) then
    if tg_table_name = 'communication_messages' then
      if not (to_jsonb(new)->>'case_processed')::boolean then
        return new;  -- solo la marca final; la reclamación/retry no fallan
      end if;
    end if;
    if nextval('public.conc01_fail_seq') = 1 then
      raise exception 'conc01 fallo sintético en %', tg_table_name;
    end if;
  end if;
  if tg_table_name = 'case_events' then
    perform pg_advisory_xact_lock_shared(4242);  -- punto de pausa determinista
  end if;
  return new;
end $$;
""" + "".join(
    f"drop trigger if exists conc01_gate on {t};"
    f" create trigger conc01_gate before insert or update on {t} for each row execute function conc01_test_gate();"
    for t in BUSINESS_TABLES)


@pytest.fixture()
def gate(env):
    env["admin"].conn().execute(GATE_SQL)
    yield env
    env["admin"].conn().execute("".join(f"drop trigger if exists conc01_gate on {t};" for t in BUSINESS_TABLES)
                                + " select pg_advisory_unlock_all()")


def _wait_for(admin, sql, timeout=20):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if admin.conn().execute(sql).fetchone()["c"]:
            return True
        time.sleep(0.05)
    return False


def test_r2_lease_expires_inside_transaction_reclaim_blocked(gate, monkeypatch):
    """Determinista: w1 está DENTRO de la RPC (validó el testigo y ya insertó el caso) y queda
    detenido por un advisory lock; el lease vence y w2 intenta reclamar. El FOR UPDATE de w1
    bloquea a w2 hasta el COMMIT; luego w2 ve case_processed=true y no toma el mensaje."""
    from datetime import timedelta
    from app.services.safe_case_classifier import classify_pending_messages

    env = gate
    admin = env["admin"]
    ids = _seed(admin, 1)
    admin.conn().execute("select pg_advisory_lock(4242)")
    out = {}

    def run(name):
        out[name] = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)

    t1 = threading.Thread(target=run, args=("w1",))
    t1.start()
    assert _wait_for(admin, "select count(*) c from pg_stat_activity where wait_event_type='Lock' and wait_event='advisory'")
    env["lease"](timedelta(seconds=-5))  # el lease de w1 ya venció
    t2 = threading.Thread(target=run, args=("w2",))
    t2.start()
    assert _wait_for(admin, "select count(*) c from pg_stat_activity where wait_event_type='Lock'"
                            " and wait_event in ('transactionid','tuple')"), "w2 no quedó bloqueado por la fila"
    mid = _invariants(admin)
    assert mid["cases"] == 0 and mid["events"] == 0  # nada visible a medio camino
    admin.conn().execute("select pg_advisory_unlock(4242)")
    t1.join(30); t2.join(30)
    assert out["w1"]["processed"] == 1 and out["w1"]["lost_claims"] == 0, out["w1"]
    assert out["w2"]["processed"] == 0 and out["w2"]["skipped_claimed"] == 1, out["w2"]
    inv = _invariants(admin)
    assert inv["cases"] == 1 and inv["case_messages"] == 1 and inv["events"] == 1 and inv["pending"] == 0, inv
    assert inv["events_without_case"] == 0
    _assert_clean(env, inv)


def test_r2_failure_inside_transaction_rolls_back_everything(gate):
    """Un fallo a mitad de las escrituras (después del caso y del evento) revierte TODO."""
    from app.services.safe_case_classifier import classify_pending_messages

    env = gate
    admin = env["admin"]
    ids = _seed(admin, 1)
    admin.conn().execute("insert into conc01_fail values ('case_messages'); select setval('conc01_fail_seq', 1, false)")
    r1 = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
    assert r1["errors"] == 1
    inv = _invariants(admin)
    assert (inv["cases"], inv["events"], inv["notifications"], inv["participants"], inv["patterns"], inv["case_messages"]) == (0,) * 6, inv
    row = admin.conn().execute("select case_processed, triage_category from communication_messages").fetchone()
    assert row["case_processed"] is False and row["triage_category"] == "retry_pending"
    admin.conn().execute("delete from conc01_fail")
    classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
    inv = _invariants(admin)
    assert inv["cases"] == 1 == inv["case_messages"] and inv["events"] == 1 and inv["pending"] == 0, inv
    _assert_clean(env, inv)


def test_rpc_rejects_wrong_token_without_writes(env):
    """La RPC no escribe nada si el testigo no coincide (validación dentro de la transacción)."""
    ids = _seed(env["admin"], 1)
    client = _api_client(env)
    ops = [{"table": "intelligent_cases", "kind": "insert", "row": {"id": str(uuid.uuid4()), "workspace_id": WS}}]
    from app.services.safe_case_classifier import _claim_message_token
    good = _claim_message_token(client, ids[0])
    assert good
    other = "classifying:" + str(uuid.uuid4())
    base = {"p_message_id": ids[0], "p_workspace_id": WS, "p_account_id": ACC, "p_ops": ops}
    for params in ({**base, "p_token": other},                                   # testigo ajeno
                   {**base, "p_token": good, "p_workspace_id": str(uuid.uuid4())},  # otro workspace
                   {**base, "p_token": good, "p_account_id": str(uuid.uuid4())}):   # otra cuenta
        r = client.rpc("conc01_commit_message", params).execute()
        assert r.data["status"] == "claim_lost", params
    assert _invariants(env["admin"])["cases"] == 0


@pytest.mark.parametrize("table", BUSINESS_TABLES)
def test_r2_error_at_each_write_rolls_back_then_retry(gate, table):
    """Tabla C: error en caso / vínculo / evento / notificación / participante / aprendizaje /
    marca final → rollback completo (0 efectos) → el reintento procesa 1 caso y 1 vínculo."""
    from app.services.safe_case_classifier import classify_pending_messages

    admin = gate["admin"]
    ids = _seed(admin, 1)
    admin.conn().execute(f"insert into conc01_fail values ('{table}'); select setval('conc01_fail_seq', 1, false)")
    r1 = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
    assert r1["errors"] == 1 and r1["processed"] == 0, r1["error_details"]
    assert admin.conn().execute("select nextval('conc01_fail_seq') n").fetchone()["n"] >= 2, r1["error_details"]
    inv = _invariants(admin)
    assert (inv["cases"], inv["case_messages"], inv["events"], inv["notifications"],
            inv["participants"], inv["patterns"]) == (0,) * 6, inv
    row = admin.conn().execute("select case_processed, triage_category from communication_messages").fetchone()
    assert row["case_processed"] is False and row["triage_category"] == "retry_pending"
    r2 = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
    inv = _invariants(admin)
    assert r2["processed"] == 1 and inv["pending"] == 0, r2
    assert inv["cases"] == 1 == inv["case_messages"] and inv["events"] == 1, inv
    assert inv["participants"] >= 1 and inv["patterns"] >= 1 and inv["notifications"] >= 1, inv
    _assert_clean(gate, inv)


def test_non_actionable_zero_cases_and_actionable_one(env):
    from app.services.safe_case_classifier import classify_pending_messages
    ids = _seed(env["admin"], 2)  # [0] accionable, [1] no accionable
    classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=[ids[1]])
    inv = _invariants(env["admin"])
    assert inv["cases"] == 0 and inv["case_messages"] == 0 and inv["events"] == 0, inv
    classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=[ids[0]])
    inv = _invariants(env["admin"])
    assert inv["cases"] == 1 and inv["case_messages"] == 1 and inv["pending"] == 0, inv
    _assert_clean(env, inv)


def test_r2_scenario_b_w1_rolls_back_w2_takes_over(gate, monkeypatch):
    """Escenario B (concurrencia real, 2 sesiones): W1 dentro de la RPC con T1 y bloqueo de fila;
    W2 espera el bloqueo para reclamar. W1 falla → ROLLBACK; W2 obtiene T2 y procesa.
    El intento posterior de W1 de escribir con T1 (marca de error) no escribe nada."""
    from datetime import timedelta
    import app.services.conc01_fenced_writes as fw
    from app.services.safe_case_classifier import classify_pending_messages

    env = gate
    admin = env["admin"]
    ids = _seed(admin, 1)
    admin.conn().execute("insert into conc01_fail values ('case_messages'); select setval('conc01_fail_seq', 1, false)")
    admin.conn().execute("select pg_advisory_lock(4242)")
    w2_done = threading.Event()
    calls = {"w1": 0}
    original = fw.commit_fenced

    def gated(*a, **k):
        if threading.current_thread().name == "w1":
            calls["w1"] += 1
            if calls["w1"] == 2:          # marca de error de W1 con T1: después de que W2 terminó
                assert w2_done.wait(30)
        return original(*a, **k)

    monkeypatch.setattr(fw, "commit_fenced", gated)
    out = {}

    def run(name):
        out[name] = classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
        if name == "w2":
            w2_done.set()

    t1 = threading.Thread(target=run, args=("w1",), name="w1")
    t1.start()
    assert _wait_for(admin, "select count(*) c from pg_stat_activity where wait_event_type='Lock' and wait_event='advisory'")
    tok1 = admin.conn().execute("select triage_reason from communication_messages").fetchone()["triage_reason"]
    env["lease"](timedelta(seconds=-5))
    t2 = threading.Thread(target=run, args=("w2",), name="w2")
    t2.start()
    assert _wait_for(admin, "select count(*) c from pg_stat_activity where wait_event_type='Lock'"
                            " and wait_event in ('transactionid','tuple')"), "w2 no quedó bloqueado por la fila"
    admin.conn().execute("select pg_advisory_unlock(4242)")  # W1 sigue y falla en case_messages → rollback
    t2.join(30); t1.join(30)
    assert not t1.is_alive() and not t2.is_alive()
    assert out["w2"]["processed"] == 1 and out["w2"]["lost_claims"] == 0, out["w2"]
    assert out["w1"]["processed"] == 0 and out["w1"]["lost_claims"] == 1, out["w1"]
    row = admin.conn().execute("select case_processed, triage_category, triage_reason from communication_messages").fetchone()
    assert row["case_processed"] is True and row["triage_category"] != "retry_pending" and row["triage_reason"] != tok1
    inv = _invariants(admin)
    assert inv["cases"] == 1 == inv["case_messages"] and inv["events"] == 1 and inv["events_without_case"] == 0, inv
    _assert_clean(env, inv)


@needs_hooks
def test_rpc_is_security_invoker_and_not_public(env):
    """Un rol sin privilegios sobre las tablas no puede usar la RPC para escribir (INVOKER),
    y PUBLIC no tiene EXECUTE."""
    admin = env["admin"]
    row = admin.conn().execute(
        "select p.prosecdef, p.proconfig, has_function_privilege('public', p.oid, 'execute') pub"
        " from pg_proc p where p.proname='conc01_commit_message'").fetchone()
    assert row["prosecdef"] is False and row["pub"] is False
    assert "search_path=pg_catalog, pg_temp" in row["proconfig"]
    admin.conn().execute("do $$ begin if not exists (select 1 from pg_roles where rolname='conc01_norights') then"
                         " create role conc01_norights; end if; end $$;"
                         " grant execute on function conc01_commit_message(uuid,uuid,uuid,text,jsonb) to conc01_norights")
    ids = _seed(admin, 1)
    import psycopg
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("set role conc01_norights")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("select conc01_commit_message(%s,%s,%s,%s,'[]'::jsonb)",
                      (ids[0], WS, ACC, "classifying:" + str(uuid.uuid4())))
    admin.conn().execute("revoke execute on function conc01_commit_message(uuid,uuid,uuid,text,jsonb) from conc01_norights")


@needs_hooks
def test_rpc_rejects_bad_params_without_leaking(env):
    import psycopg
    admin = env["admin"]
    ids = _seed(admin, 1)
    for token in (None, "x", "classifying:no-uuid"):
        with pytest.raises(psycopg.errors.InvalidParameterValue) as e:
            admin.conn().execute("select conc01_commit_message(%s,%s,%s,%s,'[]'::jsonb)", (ids[0], WS, ACC, token))
        assert "classifying" not in str(e.value).split("\n")[0].replace("conc01: testigo inválido", "")


@needs_hooks
def test_rollback_script_removes_function_keeps_data(env):
    """Rollback probado: retira función y permisos y restaura el CHECK original (NOT VALID)
    sin tocar datos; es idempotente y la migración se puede volver a aplicar."""
    from app.services.safe_case_classifier import classify_pending_messages
    admin = env["admin"]
    ids = _seed(admin, 2)
    classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids)
    # una fila reclamada en curso al momento del rollback
    admin.conn().execute(
        "insert into communication_messages (id,account_id,external_message_id,subject,triage_category,triage_reason,triaged_at)"
        " values (%s,%s,'yahoo:Inbox:9998','x','classifying','classifying:'||gen_random_uuid(), now())", (str(uuid.uuid4()), ACC))
    extra = [str(uuid.uuid4())]
    admin.conn().execute(
        "insert into communication_messages (id,account_id,thread_id,external_message_id,sender,recipients,subject,body_text,snippet,received_at,direction)"
        " select %s, account_id, thread_id, 'yahoo:Inbox:9999', sender, recipients, subject, body_text, snippet, now(), direction"
        " from communication_messages where id=%s", (extra[0], ids[0]))
    before = _invariants(admin)
    rows_before = admin.conn().execute("select id, triage_category, case_processed, triage_reason from communication_messages order by id").fetchall()
    admin.conn().execute(RPC_ROLLBACK.read_text())
    admin.conn().execute(RPC_ROLLBACK.read_text())  # idempotente
    assert admin.conn().execute("select count(*) c from pg_proc where proname='conc01_commit_message'").fetchone()["c"] == 0
    assert _invariants(admin) == before  # 0 datos de negocio afectados
    after = {r["id"]: r for r in admin.conn().execute("select id, triage_category, case_processed, triage_reason from communication_messages").fetchall()}
    for r in rows_before:  # solo cambian las filas classifying/retry_pending, y con trazabilidad
        if r["triage_category"] in ("classifying", "retry_pending"):
            assert after[r["id"]]["triage_category"] == "unreviewed"
            assert after[r["id"]]["triage_reason"] == f"conc01_rollback:{r['triage_category']}:{r['triage_reason'] or ''}"
            assert after[r["id"]]["case_processed"] == r["case_processed"]
        else:
            assert after[r["id"]] == r
    chk = admin.conn().execute("select convalidated, pg_get_constraintdef(oid) d from pg_constraint"
                               " where conname='communication_messages_triage_category_check'").fetchone()
    assert chk["convalidated"] is True and "classifying" not in chk["d"]
    # Código nuevo SIN migración (orden de despliegue incorrecto): falla cerrado antes de escribir.
    with pytest.raises(Exception) as e:
        classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=extra)
    assert "23514" in str(e.value) or "check constraint" in str(e.value)
    row = admin.conn().execute("select case_processed, triage_category from communication_messages where id=%s", (extra[0],)).fetchone()
    assert row["case_processed"] is False and row["triage_category"] == "unreviewed"
    assert _invariants(admin)["cases"] == before["cases"]
    # Reaplicar la migración de forma controlada.
    admin.conn().execute(RPC_SQL.read_text())
    assert admin.conn().execute("select count(*) c from pg_proc where proname='conc01_commit_message'").fetchone()["c"] == 1
    assert admin.conn().execute("select convalidated c from pg_constraint where conname='communication_messages_triage_category_check'").fetchone()["c"] is True


def test_prod_check_without_migration_rejects_claim(env):
    """Evidencia del hallazgo de producción: con el CHECK ORIGINAL, la reclamación de CONC-01
    ('classifying') es rechazada por la BD; la migración es requisito previo del deploy."""
    admin = env["admin"]
    ids = _seed(admin, 1)
    admin.conn().execute(RPC_ROLLBACK.read_text())
    from app.services.safe_case_classifier import _claim_message_token
    with pytest.raises(Exception) as e:
        _claim_message_token(_api_client(env), ids[0])
    assert "23514" in str(e.value) or "check constraint" in str(e.value)


def _claimed(env):
    from app.services.safe_case_classifier import _claim_message_token
    ids = _seed(env["admin"], 2)
    client = _api_client(env)
    token = _claim_message_token(client, ids[0])
    assert token
    return client, ids, token


def _case_op(case_id):
    return {"table": "intelligent_cases", "kind": "insert",
            "row": {"id": case_id, "workspace_id": WS, "account_id": ACC, "title": "x"}}


def _event_op(event_id, case_id, message_id):
    row = {"id": event_id, "workspace_id": WS, "case_id": case_id, "event_type": "case_created",
           "level": 2, "title": "t", "dedupe_key": f"case_created:{event_id}"}
    if message_id is not None:
        row["message_id"] = message_id
    return {"table": "case_events", "kind": "insert", "on_conflict": "nothing", "row": row}


def _notif_op(event_id, case_id):
    return {"table": "case_notifications", "kind": "insert",
            "row": {"id": str(uuid.uuid4()), "workspace_id": WS, "case_id": case_id, "event_id": event_id,
                    "level": 2, "channel": "dashboard", "title": "t"}}


def _call(client, ids, token, ops):
    return client.rpc("conc01_commit_message", {"p_message_id": ids[0], "p_workspace_id": WS,
                                                "p_account_id": ACC, "p_token": token, "p_ops": ops}).execute()


def _zero_writes(env, token, ids):
    inv = _invariants(env["admin"])
    assert (inv["cases"], inv["events"], inv["notifications"], inv["case_messages"]) == (0, 0, 0, 0), inv
    row = env["admin"].conn().execute("select case_processed, triage_reason from communication_messages where id=%s",
                                      (ids[0],)).fetchone()
    assert row["case_processed"] is False and row["triage_reason"] == token


def _expect_reject(env, client, ids, token, ops):
    with pytest.raises(Exception) as e:
        r = _call(client, ids, token, ops)
        if isinstance(r.data, dict) and r.data.get("status") == "ok":
            pass  # caerá en el assert de abajo
        raise AssertionError(f"no rechazó: {r.data}")
    assert "no rechazó" not in str(e.value), e.value
    assert "42501" in str(e.value) or "conc01" in str(e.value)
    _zero_writes(env, token, ids)


def test_neg_event_without_message_id_rejected(env):
    client, ids, token = _claimed(env)
    c = str(uuid.uuid4())
    _expect_reject(env, client, ids, token, [_case_op(c), _event_op(str(uuid.uuid4()), c, None)])


def test_neg_event_of_other_message_rejected(env):
    client, ids, token = _claimed(env)
    c = str(uuid.uuid4())
    _expect_reject(env, client, ids, token, [_case_op(c), _event_op(str(uuid.uuid4()), c, ids[1])])


def test_neg_notification_with_event_of_other_message_rejected(env):
    """El evento existe (creado por otro mensaje) pero no pertenece a p_message_id."""
    client, ids, token = _claimed(env)
    c, ev = str(uuid.uuid4()), str(uuid.uuid4())
    env["admin"].conn().execute("insert into intelligent_cases (id, workspace_id, account_id, title) values (%s,%s,%s,'x')", (c, WS, ACC))
    env["admin"].conn().execute("insert into case_events (id, workspace_id, case_id, message_id, event_type, title) values (%s,%s,%s,%s,'x','t')",
                                (ev, WS, c, ids[1]))
    before = _invariants(env["admin"])
    with pytest.raises(Exception) as e:
        _call(client, ids, token, [_notif_op(ev, c)])
    assert "42501" in str(e.value) or "conc01" in str(e.value)
    assert _invariants(env["admin"]) == before


def test_neg_notification_with_case_different_from_event_rejected(env):
    client, ids, token = _claimed(env)
    c1, c2, ev = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _expect_reject(env, client, ids, token,
                   [_case_op(c1), _case_op(c2), _event_op(ev, c1, ids[0]), _notif_op(ev, c2)])


def test_neg_notification_without_event_rejected(env):
    client, ids, token = _claimed(env)
    c = str(uuid.uuid4())
    n = _notif_op(None, c)
    n["row"].pop("event_id")
    _expect_reject(env, client, ids, token, [_case_op(c), n])


def test_valid_event_dedupe_still_skips_notification(env):
    """Dedupe válido: evento repetido (mismo case_id+dedupe_key) → ON CONFLICT, sin notificación doble."""
    client, ids, token = _claimed(env)
    c, ev_old, ev_new = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    admin = env["admin"]
    admin.conn().execute("insert into intelligent_cases (id, workspace_id, account_id, title) values (%s,%s,%s,'x')", (c, WS, ACC))
    admin.conn().execute("insert into case_events (id, workspace_id, case_id, message_id, event_type, dedupe_key, title)"
                         " values (%s,%s,%s,%s,'case_created','k1','t')", (ev_old, WS, c, ids[0]))
    dup = _event_op(ev_new, c, ids[0]); dup["row"]["dedupe_key"] = "k1"
    r = _call(client, ids, token, [dup, _notif_op(ev_new, c)])
    assert r.data["status"] == "ok" and r.data["skipped"] == 1, r.data
    inv = _invariants(admin)
    assert inv["events"] == 1 and inv["notifications"] == 0, inv


def test_h1_participant_case_id_is_immutable(env):
    """H1: un UPDATE de case_participants no puede mover el participante a otro caso
    (aquí, de otro workspace): rechazo y rollback completo, 0 escrituras persistentes."""
    client, ids, token = _claimed(env)
    admin = env["admin"]
    ws2, c1, c2, p1 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    admin.conn().execute("insert into workspaces values (%s)", (ws2,))
    admin.conn().execute("insert into intelligent_cases (id, workspace_id, account_id, title) values (%s,%s,%s,'a')", (c1, WS, ACC))
    admin.conn().execute("insert into intelligent_cases (id, workspace_id, title) values (%s,%s,'b')", (c2, ws2))
    admin.conn().execute("insert into case_participants (id, case_id, email) values (%s,%s,'x@y.mx')", (p1, c1))
    before = _invariants(admin)
    snap = admin.conn().execute("select * from case_participants").fetchall()
    msg = admin.conn().execute("select * from communication_messages where id=%s", (ids[0],)).fetchone()
    ops = [_case_op(str(uuid.uuid4())),  # escritura previa en el lote: también debe revertirse
           {"table": "case_participants", "kind": "update",
            "set": {"case_id": c2, "message_count": 9}, "where": {"id": p1}}]
    with pytest.raises(Exception) as e:
        _call(client, ids, token, ops)
    assert "42501" in str(e.value) or "inmutable" in str(e.value)
    assert _invariants(admin) == before
    assert admin.conn().execute("select * from case_participants").fetchall() == snap
    assert admin.conn().execute("select * from communication_messages where id=%s", (ids[0],)).fetchone() == msg
    # Los campos legítimos de _upsert_participant siguen permitidos (sin case_id, o con el mismo).
    ok = [{"table": "case_participants", "kind": "update",
           "set": {"display_name": "X", "participant_role": "requester", "message_count": 2,
                   "last_seen_at": "2026-10-31T00:00:00Z"}, "where": {"id": p1}}]
    assert _call(client, ids, token, ok).data["status"] == "ok"
    row = admin.conn().execute("select case_id, message_count from case_participants where id=%s", (p1,)).fetchone()
    assert str(row["case_id"]) == c1 and row["message_count"] == 2


def test_h2_rollback_normalizes_states_then_old_code_updates_ok(env):
    """H2: filas en classifying y retry_pending → rollback → 'unreviewed' con trazabilidad, sin tocar
    case_processed; después, las escrituras de triage del código anterior no dan 23514; no se pierden
    casos, vínculos, eventos ni datos."""
    from app.services.safe_case_classifier import classify_pending_messages
    admin = env["admin"]
    ids = _seed(admin, 4)
    classify_pending_messages(account_id=ACC, workspace_id=WS, message_ids=ids[:2])  # 1 caso real + 1 sin caso
    extra = []
    for n, (state, processed) in enumerate([("classifying", False), ("retry_pending", False), ("retry_pending", True)]):
        mid = str(uuid.uuid4()); extra.append((mid, state, processed))
        admin.conn().execute(
            "insert into communication_messages (id,account_id,external_message_id,subject,triage_category,triage_reason,triaged_at,case_processed)"
            " values (%s,%s,%s,'x',%s,%s, now(), %s)",
            (mid, ACC, f"yahoo:Inbox:{8000+n}", state, f"motivo {n}" if n else "classifying:" + str(uuid.uuid4()), processed))
    biz = lambda: admin.conn().execute(  # noqa: E731
        "select (select count(*) from intelligent_cases) c, (select count(*) from case_messages) l,"
        " (select count(*) from case_events) e, (select count(*) from case_notifications) n,"
        " (select count(*) from case_participants) p, (select count(*) from organizational_patterns) o,"
        " (select md5(string_agg(id::text||coalesce(subject,'')||coalesce(body_text,'')||case_processed::text, ',' order by id))"
        "  from communication_messages) m").fetchone()
    before = biz()
    prev = {r["id"]: r for r in admin.conn().execute("select id, triage_reason from communication_messages").fetchall()}
    admin.conn().execute(RPC_ROLLBACK.read_text())
    assert biz() == before  # casos, vínculos, eventos, notificaciones, participantes, patrones y mensajes intactos
    for mid, state, processed in extra:
        r = admin.conn().execute("select triage_category, triage_reason, case_processed from communication_messages where id=%s", (mid,)).fetchone()
        assert r["triage_category"] == "unreviewed" and r["case_processed"] is processed
        assert r["triage_reason"] == f"conc01_rollback:{state}:{prev[uuid.UUID(mid)]['triage_reason'] or ''}"
    assert admin.conn().execute("select count(*) c from communication_messages where triage_category in ('classifying','retry_pending')").fetchone()["c"] == 0
    assert admin.conn().execute("select convalidated c from pg_constraint where conname='communication_messages_triage_category_check'").fetchone()["c"] is True
    # Escrituras representativas del código anterior (main): marca sin caso, triage accionable y revisión.
    client = _api_client(env)
    for (mid, _, _), cat in zip(extra, ("informational", "action_required", "review")):
        client.table("communication_messages").update(
            {"triage_category": cat, "actionability_score": 10, "triage_reason": "código anterior", "triaged_at": "2026-10-31T00:00:00Z",
             "processed_at": "2026-10-31T00:00:00Z", "case_processed": True}).eq("id", mid).execute()
    cats = {r["triage_category"] for r in admin.conn().execute(
        "select triage_category from communication_messages where id = any(%s::uuid[])", ([m for m, _, _ in extra],)).fetchall()}
    assert cats == {"informational", "action_required", "review"}
    # Y un estado de CONC-01 vuelve a estar prohibido (el CHECK original está vigente).
    with pytest.raises(Exception) as e:
        client.table("communication_messages").update({"triage_category": "classifying"}).eq("id", extra[0][0]).execute()
    assert "23514" in str(e.value)


@pytest.mark.parametrize("table,col", [
    ("intelligent_cases", "workspace_id"), ("intelligent_cases", "account_id"),
    ("intelligent_cases", "primary_thread_id"), ("organizational_patterns", "workspace_id"),
    ("communication_messages", "account_id"), ("communication_messages", "thread_id"),
    ("case_participants", "case_id")])
def test_ownership_columns_immutable_on_update(env, table, col):
    """Autorrevisión: ninguna columna de propiedad/FK puede cambiarse por UPDATE en la RPC."""
    client, ids, token = _claimed(env)
    admin = env["admin"]
    ws2, acc2, c1, c2, th2, pat, p1 = (str(uuid.uuid4()) for _ in range(7))
    admin.conn().execute("insert into workspaces values (%s)", (ws2,))
    admin.conn().execute("insert into communication_accounts (id, workspace_id) values (%s,%s)", (acc2, ws2))
    admin.conn().execute("insert into communication_threads values (%s)", (th2,))
    admin.conn().execute("insert into intelligent_cases (id, workspace_id, account_id, title) values (%s,%s,%s,'a')", (c1, WS, ACC))
    admin.conn().execute("insert into intelligent_cases (id, workspace_id, title) values (%s,%s,'b')", (c2, ws2))
    admin.conn().execute("insert into case_participants (id, case_id, email) values (%s,%s,'x@y.mx')", (p1, c1))
    admin.conn().execute("insert into organizational_patterns (id, workspace_id, pattern_type, pattern_key) values (%s,%s,'t','k')", (pat, WS))
    target = {"intelligent_cases": c1, "organizational_patterns": pat, "communication_messages": ids[0],
              "case_participants": p1}[table]
    value = {"workspace_id": ws2, "account_id": acc2, "primary_thread_id": th2, "thread_id": th2, "case_id": c2}[col]
    dump = lambda: [admin.conn().execute(f"select * from {t} order by id").fetchall() for t in BUSINESS_TABLES]  # noqa: E731
    before = dump()
    with pytest.raises(Exception) as e:
        _call(client, ids, token, [_case_op(str(uuid.uuid4())),
                                    {"table": table, "kind": "update", "set": {col: value}, "where": {"id": target}}])
    assert "42501" in str(e.value) or "inmutable" in str(e.value)
    assert dump() == before  # rollback completo, 0 escrituras persistentes


def test_case_insert_with_foreign_thread_rejected(env):
    client, ids, token = _claimed(env)
    th2 = str(uuid.uuid4())
    env["admin"].conn().execute("insert into communication_threads values (%s)", (th2,))
    op = _case_op(str(uuid.uuid4())); op["row"]["primary_thread_id"] = th2
    with pytest.raises(Exception) as e:
        _call(client, ids, token, [op])
    assert "42501" in str(e.value) or "hilo" in str(e.value)
    _zero_writes(env, token, ids)
