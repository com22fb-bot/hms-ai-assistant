"""Mundo sintético para los ensayos de BD de ronda 3 (datos 100 % sintéticos).

Las comparaciones usan hash md5 de la fila completa (todas las columnas,
incluidos valores cifrados de credenciales). Los mensajes de error solo
muestran tabla e id, nunca valores.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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
