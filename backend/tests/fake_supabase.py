"""Cliente Supabase falso en memoria (subset de PostgREST) para pruebas unitarias."""
from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace
from typing import Any


class UniqueViolation(Exception):
    code = "23505"


class _Query:
    def __init__(self, db: "FakeSupabase", table: str):
        self.db, self.table, self.filters, self.op, self.payload, self._limit = db, table, [], "select", None, None

    def select(self, *_a, **_k):
        self.op = "select"; return self

    def update(self, payload, **_k):
        self.op, self.payload = "update", payload; return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload; return self

    def delete(self):
        self.op = "delete"; return self

    def eq(self, col, val):
        if "->>" in col:  # filtro JSON de PostgREST (metadata->>clave)
            column, key = col.split("->>", 1)
            self.filters.append(lambda r: str((r.get(column) or {}).get(key)) == str(val)); return self
        self.filters.append(lambda r: str(r.get(col)) == str(val)); return self

    def gt(self, col, val):
        self.filters.append(lambda r: str(r.get(col)) > str(val)); return self

    def neq(self, col, val):
        self.filters.append(lambda r: str(r.get(col)) != str(val)); return self

    def is_(self, col, val):
        want_null = str(val).lower() == "null"
        self.filters.append(lambda r: (r.get(col) is None) == want_null); return self

    def gte(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and str(r.get(col)) >= str(val)); return self

    def lte(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and str(r.get(col)) <= str(val)); return self

    def lt(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and str(r.get(col)) < str(val)); return self

    def or_(self, expr):
        """Subconjunto de PostgREST or=(a.op.v,b.op.v): is.null, eq, neq, lt, gt (valores entre comillas)."""
        conds = []
        for part in [p for p in expr.split(",") if p]:
            col, op, val = part.split(".", 2)
            val = val.strip('"')
            if op == "is":
                conds.append(lambda r, c=col, v=val: (r.get(c) is None) == (v.lower() == "null"))
            elif op in ("eq", "neq", "lt", "gt"):
                def f(r, c=col, o=op, v=val):
                    x = r.get(c)
                    if x is None:
                        return False  # SQL: NULL op v no es verdadero
                    x = str(x)
                    return {"eq": x == v, "neq": x != v, "lt": x < v, "gt": x > v}[o]
                conds.append(f)
            else:
                raise NotImplementedError(f"or_: operador {op}")
        self.filters.append(lambda r: any(c(r) for c in conds)); return self

    def in_(self, col, vals):
        vals = {str(v) for v in vals}
        self.filters.append(lambda r: str(r.get(col)) in vals); return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n; return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        self.db.calls.append((self.table, self.op, copy.deepcopy(self.payload)))
        if self.op == "insert":
            row = self.db._derive(self.table, {"id": str(uuid.uuid4()), **self.payload})
            self.db._check_unique(self.table, row, rows)
            rows.append(row)
            return SimpleNamespace(data=[copy.deepcopy(row)])
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == "update":
            for r in hit:
                self.db._check_unique(self.table, self.db._derive(self.table, {**r, **self.payload}), rows)
            for r in hit:
                r.update(self.payload)
                self.db._derive(self.table, r)
        elif self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if r not in hit]
        if self._limit is not None:
            hit = hit[: self._limit]
        return SimpleNamespace(data=copy.deepcopy(hit))


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None):
        self.tables = tables or {}
        for name, rows in self.tables.items():
            for row in rows:
                self._derive(name, row)
        self.calls: list[tuple[str, str, Any]] = []

    def _derive(self, table, row):
        """Columnas generadas de producción (communication_accounts.address_key)."""
        if table == "communication_accounts":
            base = (row.get("email") or "").strip(" ") or str(row.get("provider_account_id") or "")
            row["address_key"] = base.strip(" ").lower()
        return row

    def _check_unique(self, table, row, rows):
        """Índice único parcial ux_comm_accounts_live_address."""
        if table != "communication_accounts" or row.get("status") not in ("active", "needs_reauth"):
            return
        for other in rows:
            if (other.get("id") != row.get("id") and other.get("status") in ("active", "needs_reauth")
                    and other.get("provider") == row.get("provider")
                    and self._derive(table, dict(other))["address_key"] == row["address_key"]):
                raise UniqueViolation("duplicate key value violates unique constraint (23505)")

    def table(self, name):
        return _Query(self, name)

    def rpc(self, fn, params):
        """Emula public.conc01_commit_message (CONC-01 R2): valida y aplica todo o nada."""
        if fn != "conc01_commit_message":
            raise NotImplementedError(fn)
        db = self

        def run():
            msgs = db.tables.setdefault("communication_messages", [])
            m = next((r for r in msgs if str(r.get("id")) == str(params["p_message_id"])), None)
            acc = next((r for r in db.tables.get("communication_accounts", [])
                        if str(r.get("id")) == str(params["p_account_id"])), None)
            if (m is None or bool(m.get("case_processed")) or m.get("triage_reason") != params["p_token"]
                    or str(m.get("account_id")) != str(params["p_account_id"])
                    or acc is None or str(acc.get("workspace_id")) != str(params["p_workspace_id"])):
                return {"status": "claim_lost"}
            snapshot = copy.deepcopy(db.tables)
            deduped, skipped = set(), 0
            try:
                for op in params["p_ops"]:
                    t, rows = op["table"], db.tables.setdefault(op["table"], [])
                    if op["kind"] == "insert":
                        row = copy.deepcopy(op["row"])
                        if t in ("case_events", "case_messages") and str(row.get("message_id")) != str(params["p_message_id"]):
                            raise PermissionError("conc01: mensaje no coincide")
                        if t == "case_events" and any(
                                r.get("case_id") == row.get("case_id") and row.get("dedupe_key")
                                and r.get("dedupe_key") == row.get("dedupe_key") for r in rows):
                            deduped.add(str(row["id"])); continue
                        if t == "case_notifications":
                            if not row.get("event_id"):
                                raise PermissionError("conc01: notificación sin evento")
                            if str(row["event_id"]) in deduped:
                                skipped += 1; continue
                            ev = next((e for e in db.tables.get("case_events", []) if str(e.get("id")) == str(row["event_id"])), None)
                            if not ev or str(ev.get("message_id")) != str(params["p_message_id"]) \
                                    or str(ev.get("case_id")) != str(row.get("case_id")):
                                raise PermissionError("conc01: evento de la notificación no corresponde")
                        rows.append(db._derive(t, {"id": str(uuid.uuid4()), **row}))
                    else:
                        if t == "communication_messages" and str(op["where"].get("id")) != str(params["p_message_id"]):
                            raise PermissionError("conc01: update de otro mensaje")
                        for r in rows:
                            if all(str(r.get(k)) == str(v) for k, v in op["where"].items()):
                                r.update(copy.deepcopy(op["set"]))
            except Exception:
                db.tables = snapshot
                raise
            return {"status": "ok", "skipped": skipped}

        return SimpleNamespace(execute=lambda: SimpleNamespace(data=run()))
