"""Ensayo de consolidación (002a/002b/rollback) con datos 100 % sintéticos.

Las comparaciones usan hash md5 de la fila completa (todas las columnas,
incluidos valores cifrados de credenciales). Los mensajes de error solo
muestran tabla e id, nunca valores.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.db.conftest import PREP

T0 = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
PRESERVED = ["communication_accounts", "oauth_credentials", "communication_threads", "communication_messages",
             "intelligent_cases", "case_events", "case_participants", "case_messages", "case_notifications",
             "donexto_preferences"]


def _u():
    return str(uuid.uuid4())


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def run(conn, filename):
    conn.execute((PREP / filename).read_text())


def snapshot(conn):
    out = {}
    for t in PRESERVED:
        key = "profile_id" if t == "donexto_preferences" else "id"
        out[t] = dict(conn.execute(f"select {key}::text, md5(to_jsonb(x)::text) from public.{t} x").fetchall())
    return out


def assert_preserved(before, after, allowed_changed=frozenset(), allowed_removed=frozenset()):
    """Toda fila previa sigue igual (mismo hash), salvo cambios/borrados permitidos."""
    problems = []
    for t, rows in before.items():
        for rid, h in rows.items():
            if (t, rid) in allowed_removed:
                continue
            if rid not in after[t]:
                problems.append(f"{t}:{rid}:perdida")
            elif after[t][rid] != h and (t, rid) not in allowed_changed:
                problems.append(f"{t}:{rid}:modificada")
    assert not problems, problems


class World:
    def __init__(self, c):
        self.c = c
        self.p = _u()
        c.execute("insert into profiles (id, email) values (%s, 'viva@example.test')", (self.p,))
        self.ws_live = self.ws([self.p])
        self.live = self.account(self.ws_live, "G", "google")
        self.orphans = [self.account(self.ws(), "G", "google") for _ in range(3)]
        for acc in [self.live, *self.orphans]:
            for i in range(1, 9):
                self.msg(acc, f"m{i}", f"t{(i + 1) // 2}")
        self.msg(self.orphans[2], "m9", "t9")
        self.msg(self.orphans[2], "m10", "t9")
        c.execute("insert into donexto_preferences (profile_id, workspace_id, preferences) values (%s,%s,'{\"a\":1}')",
                  (self.p, self.ws_live))

        # caso canónico existente K1 (event_key + hilo t1) con evento, participante y notificación
        self.k1 = self.case(self.live, "factura-123", "t1", title="Factura")
        self.link(self.k1, self.live, "m1")
        self.event(self.k1, self.live, "m1", "creado", T0)
        self.part(self.k1, "p@example.test")
        self.notif(self.k1, "aviso A", T0)
        # dos casos canónicos con la misma identidad => ambigüedad
        self.k2 = self.case(self.live, "dup-key", "t3")
        self.k3 = self.case(self.live, "dup-key", "t3")

        # en cada copia: el mismo caso (misma identidad que K1) con datos duplicados y extra
        self.orphan_cases = []
        for i, acc in enumerate(self.orphans):
            cs = self.case(acc, "factura-123", "t1", title="Factura")
            self.orphan_cases.append(cs)
            self.link(cs, acc, "m1")
            self.link(cs, acc, "m9" if i == 2 else "m2")
            self.event(cs, acc, "m1", "creado", T0)                       # duplicado de K1
            if i < 2:
                self.event(cs, acc, "m2", "respuesta", T0 + timedelta(hours=1))  # igual en O1 y O2
                self.part(cs, "q@example.test")
                self.notif(cs, "aviso B", T0 + timedelta(hours=1))
            else:
                self.event(cs, acc, "m9", "nuevo", T0 + timedelta(hours=2))
                self.part(cs, "R@example.test")
                self.notif(cs, "aviso C", T0 + timedelta(hours=2))
            self.part(cs, "P@example.test")                               # duplicado (mayúsculas)
            self.notif(cs, "aviso A", T0)                                  # duplicado
        # mismo asunto/título que K1 pero sin identidad => caso aparte
        self.same_subject = self.case(self.orphans[0], None, "t3", title="Factura")
        self.link(self.same_subject, self.orphans[0], "m5")
        # coincide con K2 y K3 => ambiguo, se copia aparte
        self.ambiguous = self.case(self.orphans[1], "dup-key", "t3")
        self.link(self.ambiguous, self.orphans[1], "m6")

        # grupo sin canónica y grupo con dos usuarios vivos
        self.nocanon = [self.account(self.ws(), "MS", "microsoft") for _ in range(2)]
        p2 = _u()
        c.execute("insert into profiles (id) values (%s)", (p2,))
        self.p2 = p2
        self.two_live = [self.account(self.ws([self.p]), "Y", "yahoo"), self.account(self.ws([p2]), "Y", "yahoo"),
                         self.account(self.ws(), "Y", "yahoo")]
        self.other = self.account(self.ws([p2]), "SOLO", "google")

    # --- helpers
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
        self.c.execute("insert into oauth_credentials (account_id, access_token, refresh_token) "
                       "values (%s, md5(random()::text), md5(random()::text))", (aid,))
        return aid

    def tid(self, acc, ext):
        return one(self.c, "select id from communication_threads where account_id=%s and external_thread_id=%s",
                   acc, ext)

    def mid(self, acc, ext):
        return one(self.c, "select id from communication_messages where account_id=%s and external_message_id=%s",
                   acc, ext)

    def msg(self, acc, ext, thread):
        t = self.c.execute(
            "insert into communication_threads (account_id, provider, external_thread_id) values (%s,'google',%s) "
            "on conflict (account_id, external_thread_id) do update set subject=excluded.subject returning id",
            (acc, thread)).fetchone()[0]
        self.c.execute("insert into communication_messages (account_id, thread_id, provider, external_message_id, "
                       "sender, subject, body_text, labels, direction) values (%s,%s,'google',%s,'a@example.test',"
                       "'s', md5(random()::text), '[\"INBOX\"]','inbound')", (acc, t, ext))

    def case(self, acc, key, thread, title="caso"):
        cid = _u()
        meta = {} if key is None else {"event_key": key}
        import json
        self.c.execute("insert into intelligent_cases (id, workspace_id, account_id, primary_thread_id, title, "
                       "normalized_subject, metadata) select %s, workspace_id, id, %s, %s, lower(%s), %s::jsonb "
                       "from communication_accounts where id=%s",
                       (cid, self.tid(acc, thread), title, title, json.dumps(meta), acc))
        return cid

    def link(self, case, acc, ext):
        self.c.execute("insert into case_messages (case_id, message_id) values (%s,%s)", (case, self.mid(acc, ext)))

    def event(self, case, acc, ext, title, at):
        self.c.execute("insert into case_events (workspace_id, case_id, message_id, event_type, title, created_at) "
                       "select workspace_id, %s, %s, 'mensaje', %s, %s from intelligent_cases where id=%s",
                       (case, self.mid(acc, ext), title, at, case))

    def part(self, case, email):
        self.c.execute("insert into case_participants (case_id, email) values (%s,%s)", (case, email))

    def notif(self, case, title, at):
        self.c.execute("insert into case_notifications (workspace_id, case_id, title, created_at) "
                       "select workspace_id, %s, %s, %s from intelligent_cases where id=%s", (case, title, at, case))


def apply_all(conn, approve=True):
    run(conn, "002a_merge_map.sql")
    if approve:
        conn.execute("update ops_r3_merge_map set approved=true, approved_by='prueba' "
                     "where canonical_account_id is not null")
    run(conn, "002b_apply.sql")
    return one(conn, "select op_id from ops_r3_operation where script='002b_apply' order by started_at desc limit 1")


def approved_orphan_changes(w, conn):
    changed = {("communication_accounts", a) for a in w.orphans}
    removed = {("oauth_credentials", str(r[0])) for r in conn.execute(
        "select id from oauth_credentials where account_id = any(%s::uuid[])", (w.orphans,)).fetchall()}
    return changed, removed


# ------------------------------------------------------------------ mapa
def test_mapa_y_regla_de_canonica(db):
    w = World(db)
    run(db, "002a_merge_map.sql")
    rows = {r[0]: (r[1], r[2]) for r in db.execute(
        "select old_account_id::text, canonical_account_id::text, reason from ops_r3_merge_map").fetchall()}
    assert {rows[o] for o in w.orphans} == {(w.live, "huerfana_con_canonica")}
    assert {rows[a] for a in w.nocanon} == {(None, "revision_manual_sin_canonica")}
    assert not any(a in rows for a in [*w.two_live, w.live, w.other])
    with pytest.raises(Exception):   # no se puede aprobar sin canónica
        db.execute("update ops_r3_merge_map set approved=true where canonical_account_id is null")


def test_sin_aprobacion_nada_cambia(db):
    World(db)
    before = snapshot(db)
    apply_all(db, approve=False)
    assert snapshot(db) == before


# ------------------------------------------------------------------ consolidación
def test_consolidacion_preserva_y_agrega(db):
    w = World(db)
    before = snapshot(db)
    nocanon_creds = one(db, "select count(*) from oauth_credentials where account_id = any(%s::uuid[])", w.nocanon)
    changed, removed = approved_orphan_changes(w, db)
    op = apply_all(db)
    after = snapshot(db)

    # 1) nada previo se pierde ni se modifica, salvo estado de copias aprobadas y sus credenciales
    assert_preserved(before, after, changed, removed)
    # credenciales retiradas: respaldadas fila por fila con el mismo hash
    logged = dict(db.execute("select row_id::text, md5(before_row::text) from ops_r3_rows "
                             "where op_id=%s and table_name='oauth_credentials' and action='delete'", (op,)).fetchall())
    assert logged == {rid: before["oauth_credentials"][rid] for _, rid in removed}
    # 2) filas sin canónica: credenciales y estado intactos
    assert one(db, "select count(*) from oauth_credentials where account_id = any(%s::uuid[])", w.nocanon) \
        == nocanon_creds == 2
    assert one(db, "select count(*) from communication_accounts where id = any(%s::uuid[]) and status='active'",
               w.nocanon) == 2
    # 3) mensajes / hilos únicos
    assert one(db, "select count(*) from communication_messages where account_id=%s", w.live) == 10
    assert one(db, "select count(*) from communication_threads where account_id=%s", w.live) == 5
    # 4) caso K1 fusionado: eventos, participantes, notificaciones y vínculos = unión sin duplicados
    decisions = dict(db.execute("select old_case_id::text, decision from ops_r3_case_map").fetchall())
    assert [decisions[c] for c in w.orphan_cases] == ["fusionado"] * 3
    assert decisions[w.same_subject] == "copiado"
    assert decisions[w.ambiguous] == "copiado_ambiguo"
    ev = sorted(r[0] for r in db.execute("select title from case_events where case_id=%s", (w.k1,)).fetchall())
    assert ev == ["creado", "nuevo", "respuesta"]
    parts = sorted(r[0].lower() for r in db.execute("select email from case_participants where case_id=%s",
                                                   (w.k1,)).fetchall())
    assert parts == ["p@example.test", "q@example.test", "r@example.test"]
    notes = sorted(r[0] for r in db.execute("select title from case_notifications where case_id=%s",
                                            (w.k1,)).fetchall())
    assert notes == ["aviso A", "aviso B", "aviso C"]
    links = sorted(r[0] for r in db.execute(
        "select m.external_message_id from case_messages x join communication_messages m on m.id=x.message_id "
        "where x.case_id=%s", (w.k1,)).fetchall())
    assert links == ["m1", "m2", "m9"]
    # eventos copiados apuntan a mensajes de la canónica
    assert one(db, "select count(*) from case_events e join communication_messages m on m.id=e.message_id "
                   "where e.case_id=%s and m.account_id<>%s", w.k1, w.live) == 0
    # 5) casos aparte: mismo título sin identidad, y ambiguo
    assert one(db, "select count(*) from intelligent_cases where account_id=%s", w.live) == 3 + 2
    for old, ext in ((w.same_subject, "m5"), (w.ambiguous, "m6")):
        new = one(db, "select new_case_id from ops_r3_case_map where old_case_id=%s", old)
        assert str(new) not in (w.k1, w.k2, w.k3)
        assert one(db, "select m.external_message_id from case_messages x join communication_messages m "
                       "on m.id=x.message_id where x.case_id=%s", new) == ext
    # 6) V1–V5 todas en verde
    bad = [r[:2] for r in db.execute((PREP / "004_verify.sql").read_text()).fetchall() if not r[2]]
    assert not bad, bad
    # 7) cada fila nueva quedó en la bitácora con op_id y hash vigente
    assert one(db, "select count(*) from ops_r3_rows r where r.op_id=%s and r.action='insert' "
                   "and ops_r3_row_hash(r.table_name, r.row_id) is distinct from r.after_hash", op) == 0
    # 8) grupo con dos usuarios vivos intacto
    assert one(db, "select count(*) from communication_accounts where id = any(%s::uuid[]) and status='active'",
               w.two_live) == 3


def test_idempotente(db):
    World(db)
    apply_all(db)
    first = snapshot(db)
    run(db, "002b_apply.sql")
    assert snapshot(db) == first


# ------------------------------------------------------------------ rollback
def test_rollback_exacto(db):
    World(db)
    before = snapshot(db)
    op = apply_all(db)
    res = dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall())
    assert set(res) == {"reverted"}
    assert snapshot(db) == before


def test_rollback_respeta_actividad_posterior(db):
    w = World(db)
    op = apply_all(db)
    new_msg = one(db, "select row_id from ops_r3_rows where op_id=%s and table_name='communication_messages' "
                      "and action='insert' limit 1", op)
    db.execute("update communication_messages set labels='[\"INBOX\",\"STARRED\"]' where id=%s", (new_msg,))      # cambio legítimo
    copied = one(db, "select new_case_id from ops_r3_case_map where old_case_id=%s", w.same_subject)
    db.execute("insert into case_events (workspace_id, case_id, event_type, title) "
               "select workspace_id, id, 'nota', 'nota posterior' from intelligent_cases where id=%s", (copied,))
    reconnected = w.orphans[0]                                                                  # reconexión
    db.execute("update communication_accounts set status='active' where id=%s", (reconnected,))
    db.execute("insert into oauth_credentials (account_id, access_token) values (%s, md5(random()::text))",
               (reconnected,))
    res = dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall())
    report = {(r[0], str(r[1])): r[2] for r in db.execute(
        "select table_name, row_id, outcome from ops_r3_rollback_report where op_id=%s", (op,)).fetchall()}
    assert report[("communication_messages", str(new_msg))] == "skipped_changed"
    assert report[("intelligent_cases", str(copied))] == "skipped_dependents"
    assert report[("communication_accounts", reconnected)] == "skipped_changed"
    assert any(o == "skipped_conflict" for (t, _), o in report.items() if t == "oauth_credentials")
    assert res["reverted"] > 0
    # lo posterior sigue ahí
    assert one(db, "select count(*) from communication_messages where id=%s", new_msg) == 1
    assert one(db, "select count(*) from case_events where case_id=%s and title='nota posterior'", copied) == 1
    assert one(db, "select status from communication_accounts where id=%s", reconnected) == "active"
    # lo demás sí se revirtió
    assert one(db, "select count(*) from communication_accounts where id = any(%s::uuid[]) and status='superseded'",
               w.orphans) == 0


# ------------------------------------------------------------------ 001 backfill
def test_backfill_direction(db):
    w = World(db)
    for ext, labels in (("m1", '["SENT","INBOX"]'), ("m2", '["SENT"]'), ("m3", '["SENT","DRAFT"]')):
        db.execute("update communication_messages set labels=%s::jsonb where account_id=%s and external_message_id=%s",
                   (labels, w.live, ext))
    db.execute("update communication_messages set direction='draft' where account_id=%s and external_message_id='m3'",
               (w.live,))
    before = snapshot(db)
    run(db, "001_gmail_direction_backfill.sql")
    op = one(db, "select op_id from ops_r3_operation where script='001_gmail_direction_backfill'")
    assert one(db, "select count(*) from ops_r3_rows where op_id=%s", op) == 2       # m1, m2 (inbound -> outbound)
    assert one(db, "select direction from communication_messages where account_id=%s and external_message_id='m3'",
               w.live) == "draft"
    run(db, "001_gmail_direction_backfill.sql")
    assert one(db, "select count(*) from ops_r3_rows") == 2                          # idempotente
    db.execute("select * from ops_r3_rollback(%s)", (op,))
    assert snapshot(db) == before
