"""CONC-01 R2: escrituras de un mensaje reclamado, atómicas y condicionadas al testigo.

El trabajador NO escribe directamente: BufferedClient deja pasar las lecturas a la
BD y acumula todas las escrituras (insert/update) en una lista ordenada. Al final,
commit_fenced() las envía en UNA llamada RPC (public.conc01_commit_message) que, en
una sola transacción, bloquea la fila del mensaje (FOR UPDATE), valida el testigo y
aplica todo, o no aplica nada. Un SELECT previo NO se usa como fencing.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)
RPC_NAME = "conc01_commit_message"
# Orden fijo de aplicación (y de bloqueo de filas) dentro de la transacción: padres antes
# que hijos y, dentro de cada tabla, filas existentes por id. Así dos trabajadores nunca
# adquieren bloqueos de fila en orden inverso.
_PHASE = {"intelligent_cases": 0, "case_events": 1, "case_notifications": 2, "case_messages": 3,
          "case_participants": 4, "organizational_patterns": 5, "communication_messages": 6}
_PREGEN_ID = {"intelligent_cases", "case_events", "case_notifications", "case_participants",
              "organizational_patterns", "case_messages"}


class ClaimLost(RuntimeError):
    """El trabajador perdió la reclamación: no se escribió nada."""


class _Resp:
    def __init__(self, data: Any):
        self.data = data
        self.count = None


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


class _BufferedWrite:
    def __init__(self, buf: "BufferedClient", table: str, kind: str, payload: dict[str, Any]):
        self.buf, self.table, self.kind, self.payload = buf, table, kind, payload
        self.where: dict[str, Any] = {}

    def eq(self, column: str, value: Any) -> "_BufferedWrite":
        if self.kind != "update":
            raise NotImplementedError("conc01: filtro en insert")
        self.where[column] = value
        return self

    def __getattr__(self, name: str) -> Any:
        # Falla cerrado: cualquier filtro no soportado (or_, in_, neq…) no se acumula.
        raise NotImplementedError(f"conc01: '{name}' no soportado en escritura protegida")

    def execute(self) -> _Resp:
        if self.kind == "insert":
            row = dict(self.payload)
            if self.table in _PREGEN_ID and not row.get("id"):
                row["id"] = str(uuid.uuid4())
            op: dict[str, Any] = {"table": self.table, "kind": "insert", "row": _jsonable(row)}
            if self.table == "case_events":
                op["on_conflict"] = "nothing"  # dedupe_key: equivalente a ignorar 23505
            if self.table == "case_notifications" and row.get("event_id"):
                op["requires_event"] = str(row["event_id"])
            self.buf.ops.append(op)
            return _Resp([row])
        if not self.where:
            raise NotImplementedError("conc01: update sin filtro")
        self.buf.ops.append({"table": self.table, "kind": "update",
                             "set": _jsonable(self.payload), "where": _jsonable(self.where)})
        return _Resp([])


class _BufferedTable:
    def __init__(self, buf: "BufferedClient", name: str):
        self.buf, self.name = buf, name

    def select(self, *args: Any, **kwargs: Any) -> Any:
        return self.buf.inner.table(self.name).select(*args, **kwargs)

    def _before(self, op: str, payload: Any) -> None:
        hook = getattr(self.buf.inner, "before", None)  # solo el adaptador de pruebas
        if callable(hook):
            hook(self.name, op, payload)

    def insert(self, payload: dict[str, Any], **_: Any) -> _BufferedWrite:
        if not isinstance(payload, dict):
            raise NotImplementedError("conc01: insert múltiple")
        self._before("insert", payload)
        return _BufferedWrite(self.buf, self.name, "insert", payload)

    def update(self, payload: dict[str, Any], **_: Any) -> _BufferedWrite:
        self._before("update", payload)
        return _BufferedWrite(self.buf, self.name, "update", payload)

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"conc01: '{name}' no soportado en escritura protegida")


class BufferedClient:
    def __init__(self, inner: Any):
        self.inner = inner
        self.ops: list[dict[str, Any]] = []

    def table(self, name: str) -> _BufferedTable:
        return _BufferedTable(self, name)

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"conc01: '{name}' no soportado en escritura protegida")


def ordered_ops(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Orden estable: fase por tabla, inserts antes que updates, updates por id."""
    return sorted(
        ops,
        key=lambda op: (_PHASE[op["table"]], op["kind"] == "update",
                        str((op.get("where") or {}).get("id") or "") if op["table"] != "communication_messages" else ""),
    )


def commit_fenced(client: Any, message_id: str, token: str, ops: list[dict[str, Any]], *,
                  workspace_id: str, account_id: str) -> dict[str, Any]:
    """Aplica ops atómicamente si el testigo sigue vigente; si no, ClaimLost y 0 escrituras.

    Se llama después de toda la lectura/clasificación: la transacción solo dura la RPC.
    """
    started = time.perf_counter()
    try:
        response = client.rpc(
            RPC_NAME,
            {"p_message_id": str(message_id), "p_workspace_id": str(workspace_id),
             "p_account_id": str(account_id), "p_token": token, "p_ops": ordered_ops(ops)},
        ).execute()
    except Exception as error:
        logger.warning("conc01_rpc error message=%s ops=%d ms=%.1f err=%s", message_id, len(ops),
                       (time.perf_counter() - started) * 1000, type(error).__name__)
        raise
    elapsed = (time.perf_counter() - started) * 1000
    data = getattr(response, "data", None)
    if isinstance(data, list):
        data = data[0] if data else None
    if isinstance(data, dict) and RPC_NAME in data and len(data) == 1:
        data = data[RPC_NAME]
    status = data.get("status") if isinstance(data, dict) else None
    logger.info("conc01_rpc message=%s ops=%d status=%s ms=%.1f", message_id, len(ops), status, elapsed)
    if status != "ok":
        raise ClaimLost(f"reclamación perdida para {message_id}")
    return data
