"""Acceso a datos del registro de contactos (CONTACTS_V1, fase F1).

Tablas (migración ``20261127_001_contacts_v1_identity.sql``):
``message_participants``, ``contact_addresses`` y ``own_address_aliases``.

Reglas:
- Toda lectura y escritura va acotada por ``workspace_id`` (aislamiento).
- ``replace_message_participants`` es idempotente: reescribir el mismo mensaje no
  duplica filas ni hace escrituras si nada cambió.
- ``ensure_contact_address`` solo crea la identidad (dirección normalizada y su
  original). Las estadísticas son DERIVADAS y las calcula el constructor de F3;
  este módulo no ofrece ninguna vía para escribirlas.
- Un alias ``detected`` nunca rebaja ni pisa una decisión ``confirmed``/``rejected``.
- No toca ninguna tabla existente salvo para LEER ``communication_accounts``.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable

from app.services.contact_identity import identity_from_structured

MP_TABLE = "message_participants"
CA_TABLE = "contact_addresses"
ALIAS_TABLE = "own_address_aliases"

ALIAS_DETECTED, ALIAS_CONFIRMED, ALIAS_REJECTED = "detected", "confirmed", "rejected"
ALIAS_STATUSES = frozenset({ALIAS_DETECTED, ALIAS_CONFIRMED, ALIAS_REJECTED})

# Espejo del CHECK de la migración (address_norm).
_NORM_RE = re.compile(r'^[^@\s<>,;"\\]+@[a-z0-9-]+(\.[a-z0-9-]+)+$')

# Columnas que F1 compara para decidir si un participante cambió.
_PARTICIPANT_FIELDS = (
    "message_id", "workspace_id", "account_id", "role", "position", "address_original", "address_norm",
    "display_name", "parse_status", "parse_reason", "source", "provider", "direction", "occurred_at",
    "is_own", "flags",
)


class ContactRegistryError(ValueError):
    """Dato inválido o inconsistente; no se escribe nada."""


def is_valid_norm(value: object) -> bool:
    """Forma canónica exacta de F0: punto fijo de la normalización (incluida la
    equivalencia de Gmail y el dominio IDNA). Una variante sin canonizar
    (``juan.perez@gmail.com``) se rechaza para que nunca quede una fila inerte."""
    text = str(value or "")
    if not text or text != text.lower() or len(text) > 254 or not _NORM_RE.match(text):
        return False
    return canonical_address(text) == text


def canonical_address(value: object) -> str:
    """Dirección suelta (p. ej. escrita por el usuario) → address_norm de F0, o ''."""
    identity = identity_from_structured(value, None, source="fixture")
    return identity.address_norm if identity.trusted else ""


def _is_unique_violation(error: Exception) -> bool:
    code = str(getattr(error, "code", "") or "")
    return code == "23505" or "23505" in str(error) or "duplicate key" in str(error).lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_instant(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _same(field: str, a: Any, b: Any) -> bool:
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return list(a or []) == list(b or [])
    if field == "occurred_at":
        left, right = _as_instant(a), _as_instant(b)
        if left is not None and right is not None:
            return left == right  # PostgREST devuelve otro formato del mismo instante
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    return ("" if a is None else str(a)) == ("" if b is None else str(b))


class ContactRegistryRepository:
    def __init__(self, client: Any):
        self.client = client

    # ------------------------------------------------------------------ cuentas
    def list_account_emails(self, workspace_id: str) -> list[str]:
        """Correos de TODOS los buzones del workspace (también inactivos: siguen siendo propios)."""
        rows = (self.client.table("communication_accounts").select("id,email,workspace_id")
                .eq("workspace_id", workspace_id).execute().data or [])
        return [str(r.get("email") or "") for r in rows if r.get("email")]

    # ----------------------------------------------------------- participantes
    def list_message_participants(self, workspace_id: str, message_id: str) -> list[dict[str, Any]]:
        rows = (self.client.table(MP_TABLE).select("*").eq("workspace_id", workspace_id)
                .eq("message_id", message_id).execute().data or [])
        return sorted(rows, key=lambda r: (str(r.get("role")), int(r.get("position") or 0)))

    def list_participants_for_address(self, workspace_id: str, address_norm: str,
                                      limit: int = 200) -> list[dict[str, Any]]:
        if not is_valid_norm(address_norm):
            return []
        rows = (self.client.table(MP_TABLE).select("*").eq("workspace_id", workspace_id)
                .eq("address_norm", address_norm).order("occurred_at", desc=True).limit(limit)
                .execute().data or [])
        return rows

    @staticmethod
    def _validate_participant(workspace_id: str, message_id: str, row: dict[str, Any]) -> None:
        if str(row.get("workspace_id")) != str(workspace_id) or str(row.get("message_id")) != str(message_id):
            raise ContactRegistryError("participante de otro mensaje o workspace")
        status, norm = row.get("parse_status"), row.get("address_norm")
        if status == "ok":
            if not is_valid_norm(norm):
                raise ContactRegistryError("address_norm inválida")
        elif status in ("ambiguous", "invalid"):
            if norm:
                raise ContactRegistryError("una identidad no confiable no lleva address_norm")
            if row.get("is_own"):
                raise ContactRegistryError("una identidad no confiable no puede ser propia")
        else:
            raise ContactRegistryError("parse_status desconocido")

    def replace_message_participants(self, workspace_id: str, message_id: str,
                                     rows: Iterable[dict[str, Any]]) -> dict[str, int]:
        """Deja en la tabla exactamente ``rows`` para ese mensaje. Idempotente.

        Primero borra lo obsoleto o cambiado y luego inserta, para no chocar con la
        unicidad (message_id, role, address_norm) cuando cambian posiciones.
        """
        wanted = list(rows)
        keys: set[tuple[str, int]] = set()
        for row in wanted:
            self._validate_participant(workspace_id, message_id, row)
            key = (str(row["role"]), int(row["position"]))
            if key in keys:
                raise ContactRegistryError("posición duplicada en el mismo rol")
            keys.add(key)
        current = {(str(r.get("role")), int(r.get("position") or 0)): r
                   for r in self.list_message_participants(workspace_id, message_id)}
        to_delete, to_insert, unchanged = [], [], 0
        for row in wanted:
            key = (str(row["role"]), int(row["position"]))
            existing = current.get(key)
            if existing is not None and all(_same(f, existing.get(f), row.get(f)) for f in _PARTICIPANT_FIELDS):
                unchanged += 1
                continue
            if existing is not None:
                to_delete.append(existing)
            to_insert.append(row)
        to_delete.extend(r for k, r in current.items() if k not in keys)
        for row in to_delete:
            (self.client.table(MP_TABLE).delete().eq("workspace_id", workspace_id)
             .eq("message_id", message_id).eq("id", row["id"]).execute())
        for row in to_insert:
            self.client.table(MP_TABLE).insert({f: row.get(f) for f in _PARTICIPANT_FIELDS}).execute()
        return {"inserted": len(to_insert), "deleted": len(to_delete), "unchanged": unchanged}

    # ---------------------------------------------------------------- contactos
    def get_contact_address(self, workspace_id: str, address_norm: str) -> dict[str, Any] | None:
        if not is_valid_norm(address_norm):
            return None
        rows = (self.client.table(CA_TABLE).select("*").eq("workspace_id", workspace_id)
                .eq("address_norm", address_norm).limit(1).execute().data or [])
        return rows[0] if rows else None

    def list_contact_addresses(self, workspace_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return (self.client.table(CA_TABLE).select("*").eq("workspace_id", workspace_id)
                .order("address_norm").limit(limit).execute().data or [])

    def ensure_contact_address(self, workspace_id: str, address_norm: str,
                               address_original: str) -> tuple[dict[str, Any], bool]:
        """(fila, creada). Solo identidad; nunca estadísticas ni nombre como clave."""
        if not is_valid_norm(address_norm):
            raise ContactRegistryError("address_norm inválida")
        existing = self.get_contact_address(workspace_id, address_norm)
        if existing is not None:
            return existing, False
        payload = {
            "workspace_id": workspace_id,
            "address_norm": address_norm,
            "originals": [str(address_original or address_norm)[:998]],
        }
        try:
            data = self.client.table(CA_TABLE).insert(payload).execute().data or []
        except Exception as error:  # carrera: otro proceso la creó primero
            if not _is_unique_violation(error):
                raise
            existing = self.get_contact_address(workspace_id, address_norm)
            if existing is None:
                raise
            return existing, False
        return (data[0] if data else payload), True

    # -------------------------------------------------------------------- alias
    def list_aliases(self, workspace_id: str) -> list[dict[str, Any]]:
        return (self.client.table(ALIAS_TABLE).select("*").eq("workspace_id", workspace_id)
                .execute().data or [])

    def get_alias(self, workspace_id: str, address_norm: str) -> dict[str, Any] | None:
        rows = (self.client.table(ALIAS_TABLE).select("*").eq("workspace_id", workspace_id)
                .eq("address_norm", address_norm).limit(1).execute().data or [])
        return rows[0] if rows else None

    def record_detected_alias(self, workspace_id: str, address_norm: str,
                              evidence: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Registra una SUGERENCIA. Si ya existe (en cualquier estado) no la cambia."""
        if not is_valid_norm(address_norm):
            raise ContactRegistryError("address_norm inválida")
        existing = self.get_alias(workspace_id, address_norm)
        if existing is not None:
            return existing, False
        payload = {"workspace_id": workspace_id, "address_norm": address_norm,
                   "status": ALIAS_DETECTED, "evidence": dict(evidence or {})}
        try:
            data = self.client.table(ALIAS_TABLE).insert(payload).execute().data or []
        except Exception as error:
            if not _is_unique_violation(error):
                raise
            existing = self.get_alias(workspace_id, address_norm)
            if existing is None:
                raise
            return existing, False
        return (data[0] if data else payload), True

    def decide_alias(self, workspace_id: str, address_norm: str, status: str,
                     decided_by: str | None) -> dict[str, Any]:
        """Decisión explícita del usuario: confirmed o rejected (reversible)."""
        if status not in (ALIAS_CONFIRMED, ALIAS_REJECTED):
            raise ContactRegistryError("una decisión solo puede confirmar o rechazar")
        if not is_valid_norm(address_norm):
            raise ContactRegistryError("address_norm inválida")
        decision = {"status": status, "decided_by": decided_by, "decided_at": _now()}
        existing = self.get_alias(workspace_id, address_norm)
        if existing is None:
            payload = {"workspace_id": workspace_id, "address_norm": address_norm,
                       "evidence": {"reason": "user_declared"}, **decision}
            try:
                data = self.client.table(ALIAS_TABLE).insert(payload).execute().data or []
                return data[0] if data else payload
            except Exception as error:  # carrera: otro proceso la creó primero (Bugbot #219)
                if not _is_unique_violation(error):
                    raise
                existing = self.get_alias(workspace_id, address_norm)
                if existing is None:
                    raise
        data = (self.client.table(ALIAS_TABLE).update(decision).eq("workspace_id", workspace_id)
                .eq("address_norm", address_norm).execute().data or [])
        return data[0] if data else {**existing, **decision}
