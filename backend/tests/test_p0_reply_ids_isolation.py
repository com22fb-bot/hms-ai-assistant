"""P0 aislamiento (issue #195, PR #196): vinculación por In-Reply-To/References.

Tipo: UNITARIAS. Cliente Supabase FALSO en memoria, datos sintéticos, sin red.
No se accede a producción ni a Supabase real.
"""
from __future__ import annotations

import os

os.environ.setdefault("SUPABASE_URL", "http://127.0.0.1:9")
os.environ.setdefault("SUPABASE_SECRET_KEY", "dummy-unit-test")
os.environ["BRAIN_V1_ENABLED"] = "0"

import pytest

from app.services import case_engine as ce


class _Q:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def gte(self, col, val):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self):
        return type("R", (), {"data": self.rows})()


class FakeClient:
    def __init__(self, cases=(), msgs=(), links=()):
        self.t = {"intelligent_cases": list(cases), "communication_messages": list(msgs),
                  "case_messages": list(links)}

    def table(self, name):
        return _Q(self.t.get(name, []))

pytestmark = pytest.mark.unit


def _case(cid, ws, acc, status="in_progress"):
    return {"id": cid, "workspace_id": ws, "account_id": acc, "status": status,
            "primary_thread_id": "t-old", "last_activity_at": "2026-10-01", "metadata": {}}


def _msg(mid, acc, imid):
    return {"id": mid, "account_id": acc, "internet_message_id": imid}


def _find(client, *, acc, ws, reply_ids, thread="t-new"):
    return ce._find_case_for_message(
        client=client, account_id=acc, thread_id=thread, normalized_subject="x",
        workspace_id=ws, reply_ids=reply_ids)


def test_positivo_mismo_workspace():
    c = FakeClient(cases=[_case("cA", "wA", "accA")], msgs=[_msg("m1", "accA", "<p1@x>")],
                   links=[{"case_id": "cA", "message_id": "m1"}])
    assert _find(c, acc="accA", ws="wA", reply_ids=["<p1@x>"])["id"] == "cA"


def test_negativo_entre_workspaces():
    # Mensaje en A (cuenta accA) referencia un mensaje cuya fila case_messages
    # apunta a un caso del workspace B. No debe devolverse el caso B.
    c = FakeClient(cases=[_case("cB", "wB", "accB")], msgs=[_msg("m1", "accA", "<p1@x>")],
                   links=[{"case_id": "cB", "message_id": "m1"}])
    assert _find(c, acc="accA", ws="wA", reply_ids=["<p1@x>"]) is None
    assert ce._find_case_by_reply_ids(client=c, account_id="accA", reply_ids=["<p1@x>"],
                                      workspace_id="wA") is None


def test_negativo_entre_cuentas_sin_workspace():
    c = FakeClient(cases=[_case("cB", "wA", "accB")], msgs=[_msg("m1", "accA", "<p1@x>")],
                   links=[{"case_id": "cB", "message_id": "m1"}])
    assert _find(c, acc="accA", ws=None, reply_ids=["<p1@x>"]) is None


def test_caso_cerrado_no_se_recupera():
    c = FakeClient(cases=[_case("cA", "wA", "accA", status="closed")],
                   msgs=[_msg("m1", "accA", "<p1@x>")], links=[{"case_id": "cA", "message_id": "m1"}])
    assert _find(c, acc="accA", ws="wA", reply_ids=["<p1@x>"]) is None


@pytest.mark.parametrize("direction", ["inbound", "outbound"])
@pytest.mark.parametrize("header", ["in_reply_to", "references"])
def test_regresion_in_reply_to_y_references(direction, header):
    # Mismo workspace, buzón propio; el mensaje padre es entrante o saliente.
    parent = _msg("m1", "accA", "<p1@x>")
    parent["direction"] = direction
    c = FakeClient(cases=[_case("cA", "wA", "accA"), _case("cB", "wB", "accB")],
                   msgs=[parent], links=[{"case_id": "cA", "message_id": "m1"},
                                         {"case_id": "cB", "message_id": "m1"}])
    m = {"in_reply_to": "p1@x"} if header == "in_reply_to" else {"references_header": "<z@x> <p1@x>"}
    m["direction"] = direction
    found = _find(c, acc="accA", ws="wA", reply_ids=ce.message_reply_ids(m))
    assert found and found["id"] == "cA"
