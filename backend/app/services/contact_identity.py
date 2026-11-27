"""Interfaz de identidad para el registro de contactos (CONTACTS_V1, fase F0).

Contrato estable entre los datos de correo y el registro relacional de contactos.
Cada dirección se entrega como un :class:`AddressIdentity` con:

- ``address_original``: la dirección tal como llegó (sin minúsculas). Nunca se
  sobrescribe.
- ``address_norm``: la clave relacional (minúsculas, dominio IDNA, equivalencia
  de Gmail de ``mail_direction``). Vacía si el análisis no es confiable.
- ``display_name``: solo descriptivo. **Nunca** se usa como identidad ni para
  fusionar contactos.
- ``parse_status``: ``ok`` | ``ambiguous`` | ``invalid`` (mismos valores que el
  CHECK de ``message_participants.parse_status``).
- ``source``: de dónde salió el dato (proveedor/campo).
- ``reason`` y ``flags``: por qué se marcó así (auditable, sin datos personales).

Reglas (fail-closed):

1. Se analiza con ``email.headerregistry`` (biblioteca estándar), que separa nombre
   y dirección antes de decodificar encoded-words RFC 2047.
2. Un campo de remitente (``from``/``sender``/``reply_to`` único) debe contener
   exactamente un buzón válido y ningún defecto grave. Dos o más buzones →
   ``ambiguous``; nada interpretable → ``invalid``. Nunca se elige "el primero".
3. La identidad nunca se deduce del nombre visible: si el nombre contiene algo con
   forma de dirección se conserva como texto y se marca la bandera
   ``display_name_contains_address`` (indicio de suplantación, no identidad).
4. Solo las identidades ``ok`` llevan ``address_norm``; el registro solo consolida
   esas (las demás se guardan para auditoría sin crear contacto).

Dependencia H01 (PR #218, abierto, NO fusionado): la cadena guardada en
``communication_messages.sender`` hoy se escribe con ``_format_sender`` (sin
comillas), que es justo el defecto H01. Por eso :func:`identity_from_stored_sender`
es deliberadamente más estricta que ``sender_identity.parse_sender`` del PR #218:
la forma heredada sin comillas con coma en el nombre (``Perez, Juan <j@x>``) queda
``ambiguous`` (``reason='legacy_unquoted'``) en lugar de aceptarse. Cuando #218 se
fusione, esa forma podrá aceptarse delegando en ``sender_identity`` (ver
``docs/auditorias/contactos/F0_F1.md``); el contrato que debe cumplirse está en
``tests/test_contacts_f0_identity.py::test_contrato_h01_*``.

Analizar bien una dirección NO prueba que el remitente sea auténtico
(SPF/DKIM/DMARC quedan fuera de este módulo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from email import errors as email_errors
from email.headerregistry import Address, HeaderRegistry
from typing import Any, Iterable

from app.services.mail_direction import normalize_address as _gmail_equivalence

PARSE_OK = "ok"
PARSE_AMBIGUOUS = "ambiguous"
PARSE_INVALID = "invalid"
PARSE_STATUSES = frozenset({PARSE_OK, PARSE_AMBIGUOUS, PARSE_INVALID})

# Roles de participante (mismos valores que el CHECK de message_participants.role).
ROLE_FROM, ROLE_SENDER, ROLE_REPLY_TO = "from", "sender", "reply_to"
ROLE_TO, ROLE_CC, ROLE_BCC = "to", "cc", "bcc"
ROLES = (ROLE_FROM, ROLE_SENDER, ROLE_REPLY_TO, ROLE_TO, ROLE_CC, ROLE_BCC)
SINGLE_ROLES = frozenset({ROLE_FROM, ROLE_SENDER})

# Fuentes de dato admitidas (auditables; no contienen datos personales).
SOURCES = frozenset({
    "gmail_api", "microsoft_graph", "imap", "gmail_imap",
    "stored_sender", "stored_recipients", "fixture",
})

# Defectos que no vuelven ambigua una dirección única (los mismos que tolera el
# PR #218): sintaxis obsoleta interpretable y local-part no ASCII (RFC 6531).
_BENIGN_DEFECTS = (email_errors.ObsoleteHeaderDefect, email_errors.NonASCIILocalPartDefect)
_REGISTRY = HeaderRegistry()
_LEGACY_TRAILING_ANGLE = re.compile(r"^[^<>]*,[^<>]*<[^<>]*>\s*$", re.DOTALL)
_ADDRESS_LIKE = re.compile(r"[^\s@<>\"]+@[^\s@<>\"]+\.[^\s@<>\"]+")
_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_MAX_ADDRESS = 254
_MAX_LOCAL = 64
_MAX_DISPLAY = 300


@dataclass(frozen=True)
class AddressIdentity:
    address_original: str
    address_norm: str
    display_name: str
    parse_status: str
    source: str
    reason: str = "ok"
    flags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def trusted(self) -> bool:
        """Análisis no ambiguo (no implica autenticidad)."""
        return self.parse_status == PARSE_OK and bool(self.address_norm)

    @property
    def domain(self) -> str:
        return self.address_norm.rsplit("@", 1)[1] if self.trusted else ""

    def as_contract(self) -> dict[str, Any]:
        return {
            "address_original": self.address_original,
            "address_norm": self.address_norm or None,
            "display_name": self.display_name or None,
            "parse_status": self.parse_status,
            "source": self.source,
            "reason": self.reason,
            "flags": list(self.flags),
        }


class ContactIdentityError(ValueError):
    """Uso incorrecto de la interfaz (fuente o rol desconocidos)."""


def _check_source(source: str) -> str:
    if source not in SOURCES:
        raise ContactIdentityError(f"fuente no admitida: {source!r}")
    return source


def _clean_display(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1].replace('\\"', '"').replace("\\\\", "\\").strip()
    return text[:_MAX_DISPLAY]


def normalize_addr_spec(username: str, domain: str) -> tuple[str, str]:
    """(address_norm, reason). address_norm vacío si la dirección no es válida.

    Solo recibe partes ya separadas por el analizador; nunca una cadena con nombre.
    """
    local = str(username or "").strip()
    host = str(domain or "").strip().rstrip(".")
    if not local or not host:
        return "", "missing_part"
    if any(ch.isspace() or ch in "<>,;\"\\" for ch in local + host) or "@" in host or "@" in local:
        return "", "invalid_syntax"
    if host.startswith("["):
        return "", "domain_literal"
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError):
        return "", "invalid_domain"
    labels = ascii_host.split(".")
    if len(labels) < 2 or not all(_LABEL.match(label) for label in labels):
        return "", "invalid_domain"
    if len(local) > _MAX_LOCAL:
        return "", "too_long"
    candidate = f"{local.lower()}@{ascii_host}"
    norm = _gmail_equivalence(candidate)  # reutiliza la equivalencia de Gmail existente
    if not norm or "@" not in norm or len(norm) > _MAX_ADDRESS or norm != norm.lower():
        return "", "invalid_syntax"
    if norm.split("@", 1)[0] == "":
        return "", "missing_part"
    return norm, "ok"


def _parse(value: str) -> tuple[list[Address], bool]:
    """(buzones, hubo_defectos_graves). Nunca lanza."""
    try:
        header = _REGISTRY("To", value)
        addresses = list(header.addresses)
    except Exception:  # pragma: no cover - el analizador estándar no debería lanzar
        return [], True
    fatal = [d for d in header.defects if not isinstance(d, _BENIGN_DEFECTS)]
    return addresses, bool(fatal)


def _flags_for(display: str, address_norm: str) -> tuple[str, ...]:
    flags: list[str] = []
    for found in _ADDRESS_LIKE.findall(display or ""):
        if found.strip(".,;").lower() != address_norm:
            flags.append("display_name_contains_address")
            break
    return tuple(flags)


def _from_address(address: Address, original: str, source: str,
                  *, header_defects: bool) -> AddressIdentity:
    display = _clean_display(address.display_name)
    norm, reason = normalize_addr_spec(address.username, address.domain)
    raw_addr = f"{address.username}@{address.domain}" if address.username or address.domain else original
    if not norm:
        return AddressIdentity(raw_addr or original, "", display, PARSE_INVALID, source, reason)
    if header_defects:
        return AddressIdentity(raw_addr, "", display, PARSE_AMBIGUOUS, source, "header_defects")
    return AddressIdentity(raw_addr, norm, display, PARSE_OK, source, "ok", _flags_for(display, norm))


_MAX_ORIGINAL = 998  # longitud máxima de línea RFC 5322


def _unfold(value: object) -> tuple[str, bool]:
    raw = str(value or "")
    unfolded = re.sub(r"\r?\n[ \t]+", " ", raw).strip()
    bad = "\r" in unfolded or "\n" in unfolded or "\x00" in unfolded
    if len(unfolded) > _MAX_ORIGINAL:
        return unfolded[:_MAX_ORIGINAL], True
    return unfolded, bad


def identity_from_header(value: object, *, source: str, role: str = ROLE_FROM) -> AddressIdentity:
    """Campo de un único remitente (From/Sender/Reply-To único) desde la cabecera cruda."""
    _check_source(source)
    if role not in ROLES:
        raise ContactIdentityError(f"rol no admitido: {role!r}")
    raw, bad = _unfold(value)
    if not raw:
        return AddressIdentity("", "", "", PARSE_INVALID, source, "empty")
    if bad:
        return AddressIdentity(raw, "", "", PARSE_INVALID, source, "control_chars_or_too_long")
    addresses, defects = _parse(raw)
    valid = [a for a in addresses if normalize_addr_spec(a.username, a.domain)[0]]
    if len(valid) > 1:
        return AddressIdentity(raw, "", "", PARSE_AMBIGUOUS, source, "multiple")
    if not defects and len(addresses) == 1 and len(valid) == 1:
        return _from_address(valid[0], raw, source, header_defects=False)
    if len(valid) == 1:
        # Un buzón válido más fragmentos defectuosos: típicamente la forma heredada
        # sin comillas ("Perez, Juan <j@x>"). No se acepta sin la regla de H01.
        reason = "legacy_unquoted" if _LEGACY_TRAILING_ANGLE.match(raw) else "header_defects"
        return AddressIdentity(raw, "", _clean_display(valid[0].display_name), PARSE_AMBIGUOUS, source, reason)
    return AddressIdentity(raw, "", "", PARSE_INVALID, source, "no_address")


def identities_from_header_list(value: object, *, source: str) -> list[AddressIdentity]:
    """Campo de lista (To/Cc/Bcc/Reply-To) desde la cabecera cruda; un elemento por buzón."""
    _check_source(source)
    raw, bad = _unfold(value)
    if not raw:
        return []
    if bad:
        return [AddressIdentity(raw, "", "", PARSE_INVALID, source, "control_chars_or_too_long")]
    addresses, defects = _parse(raw)
    return [_from_address(a, raw, source, header_defects=defects) for a in addresses]


def identity_from_structured(email: object, name: object = None, *, source: str) -> AddressIdentity:
    """Dato ya separado por el proveedor (Graph ``emailAddress`` o jsonb ``{name,email}``).

    ``email`` debe ser exactamente una addr-spec sin nombre; ``name`` es descriptivo.
    """
    _check_source(source)
    raw, bad = _unfold(email)
    display = _clean_display(name)
    if not raw:
        return AddressIdentity("", "", display, PARSE_INVALID, source, "empty")
    if bad:
        return AddressIdentity(raw, "", display, PARSE_INVALID, source, "control_chars_or_too_long")
    addresses, defects = _parse(raw)
    valid = [a for a in addresses if normalize_addr_spec(a.username, a.domain)[0]]
    if len(valid) > 1:
        return AddressIdentity(raw, "", display, PARSE_AMBIGUOUS, source, "multiple")
    if len(addresses) != 1 or defects or addresses[0].display_name:
        status = PARSE_AMBIGUOUS if valid else PARSE_INVALID
        return AddressIdentity(raw, "", display, status, source, "not_bare_address")
    address = addresses[0]
    norm, reason = normalize_addr_spec(address.username, address.domain)
    if not norm:
        return AddressIdentity(raw, "", display, PARSE_INVALID, source, reason)
    return AddressIdentity(raw, norm, display, PARSE_OK, source, "ok", _flags_for(display, norm))


def identities_from_structured_list(entries: Iterable[Any] | None, *, source: str) -> list[AddressIdentity]:
    """Lista jsonb de ``communication_messages`` (``recipients``/``cc``/``bcc``)."""
    out: list[AddressIdentity] = []
    for entry in entries or []:
        if isinstance(entry, dict):
            out.append(identity_from_structured(entry.get("email"), entry.get("name"), source=source))
        elif isinstance(entry, str):
            # Cadena suelta: se trata como cabecera (puede traer nombre).
            out.extend(identities_from_header_list(entry, source=source))
        else:
            out.append(AddressIdentity(str(entry)[:_MAX_DISPLAY], "", "", PARSE_INVALID, source, "unsupported_type"))
    return out


def identity_from_stored_sender(value: object) -> AddressIdentity:
    """``communication_messages.sender`` (texto). Parte dependiente de H01 / PR #218.

    Igual que :func:`identity_from_header`; la forma heredada sin comillas queda
    ``ambiguous`` (``legacy_unquoted``) hasta que H01 esté fusionado y verificado.
    """
    return identity_from_header(value, source="stored_sender", role=ROLE_FROM)
