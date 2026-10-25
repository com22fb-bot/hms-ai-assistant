"""P0 #195 / PR #196: rutas de escritura de process_message.

Tipo: UNITARIAS. Cliente Supabase FALSO en memoria, datos sintéticos, sin red.
Reproduce a3, b3 y c1 (OBS-01, OBS-02) del informe rutas_escritura_informe.md.
"""
from __future__ import annotations

import os
import types
import uuid

os.environ.setdefault("SUPABASE_URL", "http://127.0.0.1:9")
os.environ.setdefault("SUPABASE_SECRET_KEY", "dummy-unit-test")
os.environ["BRAIN_V1_ENABLED"] = "0"

import pytest

from app.services import case_engine as ce

pytestmark = pytest.mark.unit

WA, WB = "ws-a", "ws-b"
A1, A2, B1 = "acc-a1", "acc-a2", "acc-b1"


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.rows = list(db.t.setdefault(name, []))
        self._op = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def __getattr__(self, name):  # gte, lte, order, like, is_, neq, ilike, contains...
        return lambda *a, **k: self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def insert(self, payload, *a, **k):
        rows = payload if isinstance(payload, list) else [payload]
        out = []
        for r in rows:
            r = {"id": str(uuid.uuid4()), **r}
            self.db.t[self.name].append(r)
            self.db.inserts.append((self.name, r))
            out.append(r)
        self.rows = out
        return self

    upsert = insert

    def update(self, *a, **k):
        return self

    def delete(self, *a, **k):
        return self

    def execute(self):
        return types.SimpleNamespace(data=self.rows, count=len(self.rows))


class FakeClient:
    def __init__(self, cases=(), msgs=(), links=()):
        self.inserts = []
        self.t = {
            "intelligent_cases": list(cases),
            "communication_messages": list(msgs),
            "case_messages": list(links),
            "communication_accounts": [
                {"id": A1, "workspace_id": WA},
                {"id": A2, "workspace_id": WA},
                {"id": B1, "workspace_id": WB},
            ],
        }

    def table(self, name):
        return _Q(self, name)

    def inserted(self, name):
        return [r for t, r in self.inserts if t == name]


def _case(cid, ws, acc, thread=None, status="new"):
    return {"id": cid, "workspace_id": ws, "account_id": acc, "status": status,
            "primary_thread_id": thread, "normalized_subject": "x",
            "last_activity_at": "2026-10-20T00:00:00+00:00", "metadata": {}}


def _msg(mid, acc, thread=None):
    return {"id": mid, "account_id": acc, "thread_id": thread, "subject": "TEST-P0ISO",
            "body_text": "texto sintetico", "sender": "T <t@example.test>",
            "direction": "inbound", "received_at": "2026-10-21T00:00:00+00:00",
            "in_reply_to": None, "references_header": []}


def test_a3_message_of_other_account_and_workspace_is_rejected():
    foreign = _case("case-b", WB, B1, thread="thr-1")
    m = _msg("m-a3", A1, thread="thr-1")
    c = FakeClient(cases=[foreign], msgs=[m])
    cid, status = ce.process_message(client=c, workspace_id=WB, account_id=B1, message=m)
    assert status == "rejected" and cid == ""
    assert c.inserted("case_messages") == [] and c.inserted("intelligent_cases") == []


def test_b3_message_of_other_account_same_workspace_is_rejected():
    own_a1 = _case("case-a1", WA, A1, thread="thr-2")
    m = _msg("m-b3", A2, thread="thr-2")
    c = FakeClient(cases=[own_a1], msgs=[m])
    cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert status == "rejected"
    assert c.inserted("case_messages") == [] and c.inserted("intelligent_cases") == []


def test_account_not_in_workspace_is_rejected():
    m = _msg("m-x", A1)
    c = FakeClient(msgs=[m])
    _, status = ce.process_message(client=c, workspace_id=WB, account_id=A1, message=m)
    assert status == "rejected" and c.inserts == []


def test_c1_already_linked_message_creates_no_orphan_case():
    own = _case("case-own", WA, A1)
    m = _msg("m-c1", A1, thread="thr-3")
    c = FakeClient(cases=[own], msgs=[m], links=[{"case_id": "case-own", "message_id": "m-c1"}])
    cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert (cid, status) == ("case-own", "already_linked")
    assert c.inserted("intelligent_cases") == [] and c.inserted("case_messages") == []


def test_valid_same_scope_message_still_links():
    own = _case("case-ok", WA, A1, thread="thr-4")
    m = _msg("m-ok", A1, thread="thr-4")
    c = FakeClient(cases=[own], msgs=[m])
    cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert (cid, status) == ("case-ok", "linked")
    assert [r["case_id"] for r in c.inserted("case_messages")] == ["case-ok"]


def test_target_case_in_other_workspace_is_rejected(monkeypatch):
    foreign = _case("case-b", WB, B1)
    m = _msg("m-t", A1)
    c = FakeClient(cases=[foreign], msgs=[m])
    monkeypatch.setattr(ce, "_find_case_for_message", lambda **k: foreign)
    cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert (cid, status) == ("", "rejected")
    assert c.inserts == [] and len(c.t["intelligent_cases"]) == 1


def test_reply_via_in_reply_to_and_references_still_links():
    own = _case("case-p", WA, A1)
    parent = {**_msg("m-parent", A1), "internet_message_id": "<p@example.test>"}
    links = [{"case_id": "case-p", "message_id": "m-parent"}]
    for hdr in ("in_reply_to", "references_header"):
        reply = {**_msg(f"m-r-{hdr}", A1), hdr: "<p@example.test>" if hdr == "in_reply_to" else ["<p@example.test>"]}
        c = FakeClient(cases=[own], msgs=[parent, reply], links=list(links))
        cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=reply)
        assert (cid, status) == ("case-p", "linked"), hdr
        assert c.inserted("intelligent_cases") == []


def test_c1_reprocess_keeps_single_link_and_new_message_still_creates_case():
    m = _msg("m-new", A1, thread="thr-9")
    c = FakeClient(msgs=[m])
    cid, status = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert status == "created"
    n_cases, n_links = len(c.t["intelligent_cases"]), len(c.t["case_messages"])
    cid2, status2 = ce.process_message(client=c, workspace_id=WA, account_id=A1, message=m)
    assert (cid2, status2) == (cid, "already_linked")
    assert len(c.t["intelligent_cases"]) == n_cases == 1
    assert [r["case_id"] for r in c.t["case_messages"]] == [cid] and n_links == 1
