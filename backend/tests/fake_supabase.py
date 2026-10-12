"""Cliente Supabase falso en memoria (subset de PostgREST) para pruebas unitarias."""
from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace
from typing import Any


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
        self.filters.append(lambda r: str(r.get(col)) == str(val)); return self

    def neq(self, col, val):
        self.filters.append(lambda r: str(r.get(col)) != str(val)); return self

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
            row = {"id": str(uuid.uuid4()), **self.payload}
            rows.append(row)
            return SimpleNamespace(data=[row])
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
        elif self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if r not in hit]
        if self._limit is not None:
            hit = hit[: self._limit]
        return SimpleNamespace(data=copy.deepcopy(hit))


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None):
        self.tables = tables or {}
        self.calls: list[tuple[str, str, Any]] = []

    def table(self, name):
        return _Query(self, name)
