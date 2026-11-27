"""Servicio mínimo del registro de contactos (CONTACTS_V1, fase F1).

Convierte un ``communication_messages`` ya guardado en participantes canónicos
(:mod:`app.services.contact_identity`) y los persiste con
:class:`ContactRegistryRepository`.

Alcance F1 (deliberadamente limitado):
- NO está enchufado a la importación, a la sincronización ni al motor de casos.
- NO calcula estadísticas (F3), NO correlaciona (F4), NO toca preferencias (F2).
- Todo método de este servicio exige ``CONTACTS_V1_ENABLED`` (por defecto ``false``);
  con la bandera apagada lanza :class:`ContactsV1Disabled` antes de tocar la BD.

Identidad propia: buzones conectados del workspace + alias ``confirmed``. Un alias
``detected`` es solo sugerencia: no es propio ni contacto externo hasta que el
usuario decida. Un alias ``rejected`` se trata como dirección externa.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from app.services import contact_identity as ci
from app.services.contact_registry_repository import (
    ALIAS_CONFIRMED,
    ALIAS_DETECTED,
    ALIAS_REJECTED,
    ContactRegistryError,
    ContactRegistryRepository,
)

_TRUE = {"1", "true", "yes", "on"}
DIRECTIONS = frozenset({"inbound", "outbound", "draft", "system"})

CLASS_CONNECTED = "connected_account"
CLASS_CONFIRMED_ALIAS = "confirmed_alias"
CLASS_DETECTED_ALIAS = "detected_alias"
CLASS_REJECTED_ALIAS = "rejected_alias"
CLASS_EXTERNAL = "external"
CLASS_UNTRUSTED = "untrusted"


def contacts_v1_enabled() -> bool:
    """Bandera CONTACTS_V1_ENABLED; apagada salvo valor explícito."""
    return os.getenv("CONTACTS_V1_ENABLED", "false").strip().lower() in _TRUE


class ContactsV1Disabled(RuntimeError):
    """El registro de contactos está apagado (CONTACTS_V1_ENABLED=false)."""


def _require_enabled() -> None:
    if not contacts_v1_enabled():
        raise ContactsV1Disabled("CONTACTS_V1_ENABLED=false")


def normalize_account_email(email: object) -> str:
    identity = ci.identity_from_structured(email, None, source="fixture")
    return identity.address_norm if identity.trusted else ""


@dataclass(frozen=True)
class OwnAddressBook:
    connected: frozenset[str]
    confirmed: frozenset[str]
    detected: frozenset[str]
    rejected: frozenset[str]

    @classmethod
    def build(cls, account_emails: Iterable[object], aliases: Iterable[dict[str, Any]]) -> "OwnAddressBook":
        connected = frozenset(a for a in (normalize_account_email(e) for e in account_emails) if a)
        by_status: dict[str, set[str]] = {ALIAS_CONFIRMED: set(), ALIAS_DETECTED: set(), ALIAS_REJECTED: set()}
        for alias in aliases or []:
            status, norm = alias.get("status"), str(alias.get("address_norm") or "")
            if status in by_status and norm and norm not in connected:
                by_status[status].add(norm)
        return cls(connected, frozenset(by_status[ALIAS_CONFIRMED]),
                   frozenset(by_status[ALIAS_DETECTED]), frozenset(by_status[ALIAS_REJECTED]))

    def classify(self, address_norm: str) -> str:
        if not address_norm:
            return CLASS_UNTRUSTED
        if address_norm in self.connected:
            return CLASS_CONNECTED
        if address_norm in self.confirmed:
            return CLASS_CONFIRMED_ALIAS
        if address_norm in self.detected:
            return CLASS_DETECTED_ALIAS
        if address_norm in self.rejected:
            return CLASS_REJECTED_ALIAS
        return CLASS_EXTERNAL

    def is_own(self, address_norm: str) -> bool:
        return self.classify(address_norm) in (CLASS_CONNECTED, CLASS_CONFIRMED_ALIAS)


def _identities_for_message(message: dict[str, Any]) -> list[tuple[str, ci.AddressIdentity]]:
    out: list[tuple[str, ci.AddressIdentity]] = []
    sender = message.get("sender")
    if str(sender or "").strip():
        out.append((ci.ROLE_FROM, ci.identity_from_stored_sender(sender)))
    for role, column in ((ci.ROLE_TO, "recipients"), (ci.ROLE_CC, "cc"), (ci.ROLE_BCC, "bcc")):
        value = message.get(column)
        if isinstance(value, (list, tuple)):
            out.extend((role, i) for i in ci.identities_from_structured_list(value, source="stored_recipients"))
    return out


def participant_rows_for_message(message: dict[str, Any], account: dict[str, Any],
                                 book: OwnAddressBook) -> list[dict[str, Any]]:
    """Filas deterministas de ``message_participants`` para un mensaje (función pura)."""
    if not message.get("id") or not account.get("id") or not account.get("workspace_id"):
        raise ContactRegistryError("mensaje o cuenta incompletos")
    if str(message.get("account_id")) != str(account.get("id")):
        raise ContactRegistryError("el mensaje no pertenece a la cuenta")
    direction = str(message.get("direction") or "inbound")
    if direction not in DIRECTIONS:
        raise ContactRegistryError("dirección de mensaje desconocida")
    occurred_at = message.get("received_at") or message.get("created_at")
    if not occurred_at:
        raise ContactRegistryError("mensaje sin fecha")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    positions: dict[str, int] = {}
    for role, identity in _identities_for_message(message):
        if identity.trusted:
            key = (role, identity.address_norm)
            if key in seen:
                continue  # duplicado en el mismo rol: se conserva el primero
            seen.add(key)
        position = positions.get(role, 0)
        positions[role] = position + 1
        rows.append({
            "message_id": str(message["id"]),
            "workspace_id": str(account["workspace_id"]),
            "account_id": str(account["id"]),
            "role": role,
            "position": position,
            "address_original": identity.address_original[:998],
            "address_norm": identity.address_norm or None,
            "display_name": identity.display_name or None,
            "parse_status": identity.parse_status,
            "parse_reason": identity.reason,
            "source": identity.source,
            "provider": (str(account.get("provider") or message.get("provider") or "") or None),
            "direction": direction,
            "occurred_at": str(occurred_at),
            "is_own": bool(identity.trusted and book.is_own(identity.address_norm)),
            "flags": list(identity.flags),
        })
    return rows


def alias_candidates(rows: Iterable[dict[str, Any]], book: OwnAddressBook) -> list[dict[str, Any]]:
    """From confiable de un ENVIADO que no es buzón conectado ni alias decidido → sugerencia."""
    out = []
    for row in rows:
        if (row.get("direction") == "outbound" and row.get("role") == ci.ROLE_FROM
                and row.get("parse_status") == "ok"
                and book.classify(str(row.get("address_norm"))) == CLASS_EXTERNAL):
            out.append({"address_norm": row["address_norm"],
                        "evidence": {"reason": "from_of_outbound", "account_id": row["account_id"],
                                     "message_id": row["message_id"]}})
    return out


def contact_candidates(rows: Iterable[dict[str, Any]], book: OwnAddressBook) -> list[dict[str, Any]]:
    """Direcciones externas confiables que pueden tener identidad en contact_addresses."""
    alias_from = {c["address_norm"] for c in alias_candidates(rows, book)}
    out, seen = [], set()
    for row in rows:
        norm = row.get("address_norm")
        if row.get("parse_status") != "ok" or not norm or row.get("is_own") or norm in seen or norm in alias_from:
            continue
        if book.classify(norm) not in (CLASS_EXTERNAL, CLASS_REJECTED_ALIAS):
            continue  # alias detectado: pendiente de decisión, no es contacto todavía
        seen.add(norm)
        out.append({"address_norm": norm, "address_original": row["address_original"]})
    return out


class ContactRegistryService:
    def __init__(self, client: Any, repository: ContactRegistryRepository | None = None):
        self.repo = repository or ContactRegistryRepository(client)

    def own_address_book(self, workspace_id: str) -> OwnAddressBook:
        _require_enabled()
        return OwnAddressBook.build(self.repo.list_account_emails(workspace_id),
                                    self.repo.list_aliases(workspace_id))

    def record_message(self, workspace_id: str, message: dict[str, Any],
                       account: dict[str, Any]) -> dict[str, Any]:
        """Participantes + identidades de un mensaje ya guardado. Idempotente. Sin estadísticas."""
        _require_enabled()
        if str(account.get("workspace_id")) != str(workspace_id):
            raise ContactRegistryError("la cuenta no pertenece al workspace")
        book = self.own_address_book(workspace_id)
        rows = participant_rows_for_message(message, account, book)
        result = self.repo.replace_message_participants(workspace_id, str(message["id"]), rows)
        aliases = [self.repo.record_detected_alias(workspace_id, c["address_norm"], c["evidence"])[1]
                   for c in alias_candidates(rows, book)]
        contacts = [self.repo.ensure_contact_address(workspace_id, c["address_norm"], c["address_original"])[1]
                    for c in contact_candidates(rows, book)]
        return {
            **result,
            "participants": len(rows),
            "untrusted": sum(1 for r in rows if r["parse_status"] != "ok"),
            "own": sum(1 for r in rows if r["is_own"]),
            "contacts_created": sum(contacts),
            "aliases_detected": sum(aliases),
        }

    def classify_address(self, workspace_id: str, address_norm: str) -> str:
        return self.own_address_book(workspace_id).classify(address_norm)

    def decide_alias(self, workspace_id: str, address_norm: str, status: str, decided_by: str | None):
        _require_enabled()
        if address_norm in self.own_address_book(workspace_id).connected:
            raise ContactRegistryError("es un buzón conectado, no un alias")
        return self.repo.decide_alias(workspace_id, address_norm, status, decided_by)

    def get_contact(self, workspace_id: str, address_norm: str):
        _require_enabled()
        return self.repo.get_contact_address(workspace_id, address_norm)

    def list_contacts(self, workspace_id: str, limit: int = 200):
        _require_enabled()
        return self.repo.list_contact_addresses(workspace_id, limit)

    def list_participants(self, workspace_id: str, message_id: str):
        _require_enabled()
        return self.repo.list_message_participants(workspace_id, message_id)
