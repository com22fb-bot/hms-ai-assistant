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

    def update(self, payload):
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

    def neq(self, col, val):
        self.filters.append(lambda r: str(r.get(col)) != str(val)); return self

    def is_(self, col, val):
        want_null = str(val).lower() == "null"
        self.filters.append(lambda r: (r.get(col) is None) == want_null); return self

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
