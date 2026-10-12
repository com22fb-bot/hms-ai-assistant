"""Ensayo de las migraciones preparadas de ronda 3 en un Postgres AISLADO.

Usa el esquema de producción (solo DDL, sin datos) exportado del catálogo y datos
100 % sintéticos. Se salta si no hay R3_TEST_DSN (p. ej.
postgresql://box:box@localhost/postgres). Nunca apunta a producción.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("R3_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="R3_TEST_DSN no definido")

HERE = Path(__file__).parent
PREP = HERE.parents[2] / "supabase" / "prepared" / "ronda3"


def _u() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def db():
    assert "supabase.co" not in (DSN or ""), "solo bases locales"
    name = "r3t_" + uuid.uuid4().hex[:10]
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
        for role in ("anon", "authenticated"):  # roles que existen en Supabase
            if not admin.execute("select 1 from pg_roles where rolname=%s", (role,)).fetchone():
                admin.execute(f"create role {role} nologin")
    dsn = DSN.rsplit("/", 1)[0] + "/" + name
    conn = psycopg.connect(dsn, autocommit=True)
    conn.execute("create extension if not exists citext")
    conn.execute("create extension if not exists pg_trgm")
    conn.execute((HERE / "schema_prod_tables.sql").read_text())
    conn.execute((HERE / "schema_prod_constraints.sql").read_text())
    try:
        yield conn
    finally:
        conn.close()
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'drop database "{name}" with (force)')


def run(conn, filename: str) -> None:
    conn.execute((PREP / filename).read_text())


def one(conn, sql: str, *args):
    return conn.execute(sql, args).fetchone()[0]


class World:
    """Réplica sintética del caso hmcelinfo: 1 fila viva + 3 copias huérfanas."""

    def __init__(self, conn):
        self.c = conn
        self.profile = _u()
        conn.execute("insert into profiles (id, email) values (%s, 'viva@example.test')", (self.profile,))
        self.ws_live = self.ws(members=[self.profile])
        self.live = self.account(self.ws_live, "g-1", "google")
        self.orphans = [self.account(self.ws(), "g-1", "google") for _ in range(3)]
        # mensajes: viva tiene m1..m8; huérfanas comparten m1..m8 y la última tiene m9, m10 únicas
        for acc in [self.live, *self.orphans]:
            for i in range(1, 9):
                self.msg(acc, f"m{i}", f"t{(i + 1) // 2}")
        self.msg(self.orphans[2], "m9", "t9")
        self.msg(self.orphans[2], "m10", "t9")
        # el mismo caso copiado en cada huérfana; la viva no tiene caso
        for acc in self.orphans:
            case = self.case(acc, "factura-123")
            self.link(case, acc, "m1")
            self.link(case, acc, "m9" if acc == self.orphans[2] else "m2")
            conn.execute(
                "insert into case_events (workspace_id, case_id, message_id, event_type, title) "
                "select workspace_id, %s, (select id from communication_messages where account_id=%s "
                "and external_message_id='m1'), 'created', 'e' from intelligent_cases where id=%s",
                (case, acc, case))
            conn.execute("insert into case_participants (case_id, email) values (%s, 'p@example.test')", (case,))
        conn.execute("insert into donexto_preferences (profile_id, workspace_id, preferences) values (%s,%s,'{}')",
                     (self.profile, self.ws_live))
        # grupo sin canónica (todas huérfanas) y grupo ambiguo (2 vivas)
        self.nocanon = [self.account(self.ws(), "o-1", "microsoft") for _ in range(2)]
        p2 = _u()
        conn.execute("insert into profiles (id) values (%s)", (p2,))
        self.amb = [self.account(self.ws(members=[self.profile]), "y-1", "yahoo"),
                    self.account(self.ws(members=[p2]), "y-1", "yahoo"),
                    self.account(self.ws(), "y-1", "yahoo")]
        self.other_live = self.account(self.ws(members=[p2]), "solo-1", "google")
        self.msg(self.other_live, "x1", "tx")

    def ws(self, members=()):
        wid = _u()
        self.c.execute("insert into workspaces (id, name) values (%s, 'w')", (wid,))
        for p in members:
            self.c.execute("insert into workspace_members (workspace_id, profile_id, status) values (%s,%s,'active')",
                           (wid, p))
        return wid

    def account(self, ws, pai, provider):
        aid = _u()
        self.c.execute("insert into communication_accounts (id, workspace_id, provider, provider_account_id, status) "
                       "values (%s,%s,%s,%s,'active')", (aid, ws, provider, pai))
        self.c.execute("insert into oauth_credentials (account_id, access_token) values (%s,'sintetico')", (aid,))
        return aid

    def msg(self, acc, ext, thread):
        tid = self.c.execute(
            "insert into communication_threads (account_id, provider, external_thread_id) values (%s,'google',%s) "
            "on conflict (account_id, external_thread_id) do update set updated_at=now() returning id",
            (acc, thread)).fetchone()[0]
        self.c.execute("insert into communication_messages (account_id, thread_id, provider, external_message_id, "
                       "sender, subject, labels, direction) values (%s,%s,'google',%s,'a@example.test','s',"
                       "'[\"INBOX\"]','inbound')", (acc, tid, ext))

    def case(self, acc, key):
        cid = _u()
        self.c.execute("insert into intelligent_cases (id, workspace_id, account_id, title, metadata) "
                       "select %s, workspace_id, id, 'caso', jsonb_build_object('event_key', %s::text) "
                       "from communication_accounts where id=%s", (cid, key, acc))
        return cid

    def link(self, case, acc, ext):
        self.c.execute("insert into case_messages (case_id, message_id) select %s, id from communication_messages "
                       "where account_id=%s and external_message_id=%s", (case, acc, ext))


def snapshot(conn):
    tables = ["communication_accounts", "oauth_credentials", "communication_threads", "communication_messages",
              "intelligent_cases", "case_messages", "case_events", "case_participants", "donexto_preferences"]
    out = {}
    for t in tables:
        cols = "status" if t == "communication_accounts" else "1"
        key = "profile_id" if t == "donexto_preferences" else "id"
        out[t] = sorted(conn.execute(f"select {key}::text, {cols}::text from {t}").fetchall())
    return out


def apply_all(conn, approve_sql="update ops_r3_merge_map set approved = true"):
    run(conn, "002a_merge_map.sql")
    conn.execute(approve_sql)
    run(conn, "002b_apply.sql")


def test_mapa_canonico(db):
    w = World(db)
    run(db, "002a_merge_map.sql")
    rows = dict(db.execute("select old_account_id::text, coalesce(canonical_account_id::text,'-') "
                           "from ops_r3_merge_map").fetchall())
    assert {rows[o] for o in w.orphans} == {w.live}
    assert all(rows[o] == "-" for o in w.nocanon)
    assert not any(a in rows for a in w.amb)          # grupo ambiguo: no se toca
    assert w.live not in rows and w.other_live not in rows
    assert one(db, "select count(*) from ops_r3_merge_map where approved") == 0


def test_sin_aprobacion_no_cambia_nada(db):
    World(db)
    before = snapshot(db)
    apply_all(db, approve_sql="select 1")
    assert snapshot(db) == before


def test_consolidacion_preserva_todo_y_v1_v5(db):
    w = World(db)
    uniq_before = one(db, "select count(distinct external_message_id) from communication_messages "
                          "where account_id = any(%s::uuid[])", [w.live, *w.orphans])
    apply_all(db)
    # mensajes e hilos únicos en la canónica
    assert one(db, "select count(distinct external_message_id) from communication_messages where account_id=%s",
               w.live) == uniq_before == 10
    assert one(db, "select count(*) from communication_messages where account_id=%s", w.live) == 10
    assert one(db, "select count(*) from communication_threads where account_id=%s", w.live) == 5
    # m9/m10 cuelgan del hilo canónico t9
    assert one(db, "select count(*) from communication_messages m join communication_threads t on t.id=m.thread_id "
                   "where m.account_id=%s and t.account_id=%s and t.external_thread_id='t9'", w.live, w.live) == 2
    # un solo caso copiado (las 3 copias eran el mismo) con sus 3 vínculos distintos
    assert one(db, "select count(*) from intelligent_cases where account_id=%s", w.live) == 1
    assert one(db, "select count(*) from case_messages cm join intelligent_cases c on c.id=cm.case_id "
                   "where c.account_id=%s", w.live) == 3
    assert one(db, "select count(*) from case_events e join intelligent_cases c on c.id=e.case_id "
                   "where c.account_id=%s and e.message_id is not null", w.live) == 1
    assert one(db, "select count(*) from case_participants p join intelligent_cases c on c.id=p.case_id "
                   "where c.account_id=%s", w.live) == 1
    assert one(db, "select count(*) from ops_r3_case_map") == 3
    # vínculos siempre a mensajes de la canónica
    assert one(db, "select count(*) from case_messages cm join intelligent_cases c on c.id=cm.case_id "
                   "join communication_messages m on m.id=cm.message_id where c.account_id=%s "
                   "and m.account_id<>%s", w.live, w.live) == 0
    # estados y credenciales
    assert one(db, "select count(*) from communication_accounts where id = any(%s::uuid[]) and status='superseded'",
               [*w.orphans, *w.nocanon]) == 5
    assert one(db, "select count(*) from oauth_credentials where account_id = any(%s::uuid[])",
               [*w.orphans, *w.nocanon]) == 0
    assert one(db, "select count(*) from ops_r3_oauth_backup") == 5
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "active"
    assert one(db, "select count(*) from communication_accounts where id = any(%s::uuid[]) and status='active'",
               w.amb) == 3
    assert one(db, "select count(*) from oauth_credentials where account_id=%s", w.live) == 1
    # V1–V5
    checks = db.execute((PREP / "004_verify.sql").read_text()).fetchall()
    failing = [c for c in checks if c[0] != "V2" and not c[2]]
    assert not failing, failing
    # V2 sigue en falso SOLO por la fila huérfana del grupo ambiguo (fuera del mapa, a revisión)
    v2 = [c for c in checks if c[0] == "V2"][0][2]
    assert v2 is False
    assert one(db, "select count(*) from communication_accounts a where status='active' and not exists "
                   "(select 1 from workspace_members m where m.workspace_id=a.workspace_id)") == 1


def test_idempotente(db):
    w = World(db)
    apply_all(db)
    first = snapshot(db)
    run(db, "002b_apply.sql")
    assert snapshot(db) == first
    assert one(db, "select count(*) from communication_messages where account_id=%s", w.live) == 10


def test_rollback_restaura_estado(db):
    World(db)
    before = snapshot(db)
    apply_all(db)
    run(db, "002_rollback.sql")
    after = snapshot(db)
    # credenciales vuelven con id nuevo? no: se restauran con su id original
    assert after == before


def test_rls_y_politicas_no_se_tocan(db):
    World(db)
    pol_before = one(db, "select count(*) from pg_policies")
    apply_all(db)
    assert one(db, "select count(*) from pg_policies") == pol_before


def test_backfill_direction_y_rollback(db):
    w = World(db)
    db.execute("update communication_messages set labels='[\"SENT\",\"INBOX\"]' where account_id=%s "
               "and external_message_id in ('m1','m2')", (w.live,))
    db.execute("update communication_messages set labels='[\"SENT\",\"DRAFT\"]', direction='draft' "
               "where account_id=%s and external_message_id='m3'", (w.live,))
    run(db, "001_gmail_direction_backfill.sql")
    assert one(db, "select count(*) from communication_messages where direction='outbound'") == 2
    assert one(db, "select direction from communication_messages where account_id=%s and external_message_id='m3'",
               w.live) == "draft"
    run(db, "001_gmail_direction_backfill.sql")  # idempotente
    assert one(db, "select count(*) from ops_r3_direction_backup") == 2
    run(db, "001_rollback.sql")
    assert one(db, "select count(*) from communication_messages where direction='outbound'") == 0


def test_trigger_huerfanas(db):
    w = World(db)
    run(db, "003_orphan_guards.sql")
    db.execute("delete from workspace_members where workspace_id=%s", (w.ws_live,))
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "inactive"
    # workspace con otro miembro activo no se toca
    run(db, "003_rollback.sql")
