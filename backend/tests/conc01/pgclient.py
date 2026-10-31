"""Cliente mínimo con la misma forma que supabase-py, sobre Postgres REAL.

Cada execute() es una sentencia autocommit en su propia conexión del cliente,
igual que una llamada PostgREST: no hay transacción que abarque varias
llamadas. Así las carreras entre hilos son reales (no simuladas).
"""
from __future__ import annotations

import json
import threading
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class Resp:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class APIError(Exception):
    pass


def _col(c: str) -> str:
    if "->>" in c:
        a, b = c.split("->>", 1)
        return f'"{a}"->>\'{b}\''
    return f'"{c}"'


def _val(v):
    return Jsonb(v) if isinstance(v, (dict, list)) else v


class Q:
    def __init__(self, client, table):
        self.c, self.t = client, table
        self.op, self.payload, self.cols = "select", None, "*"
        self.where, self.args, self._order, self._limit = [], [], None, None
        self.returning, self.count_mode = None, None
        self.post: list = []  # filtros lógicos (or=) que PostgREST reaplica a la salida

    def select(self, cols="*", **_):
        self.op, self.cols = ("select" if self.op == "select" else self.op), cols
        return self

    # Igual que postgrest-py 2.31 (request_builder.py:373/418): returning por
    # defecto = representation, salvo que el cliente se configure en "minimal"
    # para imitar Prefer: return=minimal (PostgREST responde 204 sin cuerpo).
    def insert(self, payload, *, count=None, returning=None, **_):
        self.op, self.payload = "insert", payload
        self.returning, self.count_mode = returning, count
        return self

    def update(self, payload, *, count=None, returning=None, **_):
        self.op, self.payload = "update", payload
        self.returning, self.count_mode = returning, count
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _w(self, sql, *a):
        self.where.append(sql)
        self.args.extend(a)
        return self

    def eq(self, c, v):
        return self._w(f"{_col(c)} = %s", v)

    def neq(self, c, v):
        return self._w(f"{_col(c)} is distinct from %s", v)

    def gte(self, c, v):
        return self._w(f"{_col(c)} >= %s", v)

    def lt(self, c, v):
        return self._w(f"{_col(c)} < %s", v)

    def is_(self, c, v):
        return self._w(f"{_col(c)} is null" if v in (None, "null") else f"{_col(c)} is not null")

    def in_(self, c, vals):
        vals = list(vals)
        if not vals:
            return self._w("false")
        return self._w(f"{_col(c)}::text = any(%s)", [str(v) for v in vals])

    def or_(self, expr):
        # Soporta la forma usada por el claim: "a.is.null,b.lt.<iso>,c.neq.x"
        parts, args = [], []
        for item in expr.split(","):
            col, op, val = item.split(".", 2)
            val = val.strip('"')
            if op == "is" and val == "null":
                parts.append(f"{_col(col)} is null")
            elif op == "lt":
                parts.append(f"{_col(col)} < %s"); args.append(val)
            elif op == "neq":
                parts.append(f"{_col(col)} is distinct from %s"); args.append(val)
            elif op == "eq":
                parts.append(f"{_col(col)} = %s"); args.append(val)
            else:
                raise NotImplementedError(op)
        self.post.append(("(" + " or ".join(parts) + ")", args))
        return self._w("(" + " or ".join(parts) + ")", *args)

    def order(self, c, desc=False, **_):
        self._order = f"{_col(c)} {'desc' if desc else 'asc'} nulls last"
        return self

    def limit(self, n):
        self._limit = int(n)
        return self

    def execute(self):
        self.c.before(self.t, self.op, self.payload)
        w = (" where " + " and ".join(self.where)) if self.where else ""
        if self.op == "select":
            cols = "*" if self.cols.strip() == "*" else ",".join(_col(x.strip()) for x in self.cols.split(","))
            sql = f'select {cols} from "{self.t}"{w}'
            if self._order:
                sql += f" order by {self._order}"
            if self._limit:
                sql += f" limit {self._limit}"
            args = self.args
        elif self.op == "insert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            keys = list(rows[0])
            sql = (f'insert into "{self.t}" (' + ",".join(_col(k) for k in keys) + ") values "
                   + ",".join("(" + ",".join(["%s"] * len(keys)) + ")" for _ in rows) + " returning *")
            args = [_val(r.get(k)) for r in rows for k in keys]
        elif self.op == "update":
            keys = list(self.payload)
            # Igual que PostgREST 12.2.3 (comprobado con curl): los filtros
            # LÓGICOS (or=/and=) se aplican otra vez sobre las filas devueltas
            # (WITH pgrst_source AS (UPDATE ... RETURNING *) SELECT ... WHERE (or)).
            # Si usan columnas modificadas, data=[] aunque el UPDATE ocurrió.
            post = (" where " + " and ".join(p for p, _ in self.post)) if self.post else ""
            sql = (f'with pgrst_source as (update "{self.t}" set ' + ",".join(f"{_col(k)} = %s" for k in keys)
                   + w + f' returning *) select * from pgrst_source as "{self.t}"' + post)
            args = [_val(self.payload[k]) for k in keys] + self.args + [a for _, ps in self.post for a in ps]
        else:
            sql, args = f'delete from "{self.t}"{w} returning *', self.args
        try:
            with self.c.conn().cursor() as cur:
                cur.execute(sql, args)
                data = cur.fetchall() if cur.description else []
        except psycopg.Error as e:
            raise APIError(f"{getattr(e, 'sqlstate', '')} {e}") from None
        affected = len(data)
        mode = str(self.returning or self.c.default_returning)
        if self.op in ("insert", "update", "delete") and mode.endswith("minimal"):
            data = []  # PostgREST con return=minimal: éxito sin filas en el cuerpo
        count = affected if self.count_mode else None
        data = [{k: (str(v) if k.endswith("id") and v is not None and not isinstance(v, str) else v)
                 for k, v in r.items()} for r in data]
        return Resp(data, count)


class PgClient:
    """Una conexión por hilo; hooks opcionales para inyectar fallos/pausas."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._local = threading.local()
        self.hooks: list = []
        self.default_returning = "representation"

    def conn(self):
        c = getattr(self._local, "c", None)
        if c is None or c.closed:
            c = self._local.c = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
        return c

    def before(self, table, op, payload):
        for h in self.hooks:
            h(table, op, payload)

    def table(self, name):
        return Q(self, name)

    def rpc(self, fn, params):
        client = self

        class _Rpc:
            def execute(self_inner):
                client.before(fn, "rpc", params)
                names = list(params)
                sql = f'select public."{fn}"(' + ", ".join(f"{n} => %s" for n in names) + ") as r"
                try:
                    with client.conn().cursor() as cur:
                        cur.execute(sql, [_val(params[n]) for n in names])
                        row = cur.fetchone()
                except psycopg.Error as e:
                    raise APIError(f"{getattr(e, 'sqlstate', '')} {e}") from None
                return Resp(row["r"])
        return _Rpc()
