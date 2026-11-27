"""Identidad canónica del remitente (H01, auditoría forense de ingesta 2026-11-27).

Una sola regla para construir, guardar y volver a leer ``communication_messages.sender``
en los tres proveedores (Gmail API, Microsoft Graph, IMAP Yahoo/iCloud).

Problema que corrige (H01): el remitente se guardaba como ``f"{nombre} <{email}>"``
sin comillas. Un nombre visible con coma (``aviso@banamex.com.mx, Soporte``) se volvía,
al reanalizar la cadena, una segunda dirección, y los consumidores tomaban la primera:
la dirección del nombre visible en lugar de la real. En IMAP además se decodificaban
las encoded-words RFC 2047 antes de analizar, con el mismo efecto.

Reglas:

1. El análisis usa el analizador de cabeceras de la biblioteca estándar
   (``email.headerregistry``), que separa nombre y dirección antes de decodificar
   las encoded-words RFC 2047.
2. La cadena guardada es RFC 5322: el nombre va entre comillas cuando lo necesita
   (``email.headerregistry.Address``). Se garantiza el viaje de ida y vuelta:
   ``parse_sender(format_sender(n, e)).email == e``.
3. Nunca se toma una dirección del nombre visible. Si el campo es inválido, está
   vacío o contiene varias identidades sin una regla explícita, ``email`` queda vacío
   (no se inventa ni se elige una identidad).
4. Compatibilidad con filas ya guardadas con el formato anterior
   (``Nombre, con coma <dir@dominio>``): si la cadena termina en un único
   ``<dirección>`` y el texto previo no contiene ``<`` ni ``>``, la dirección es la
   del ``<...>`` final. Es exactamente la forma que escribían los tres
   serializadores anteriores, y la dirección entre ángulos es la dirección real
   (RFC 5322 name-addr); el nombre visible nunca aporta la dirección.

Analizar bien una dirección NO prueba que el remitente sea auténtico (SPF/DKIM/DMARC
quedan fuera de este módulo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from email.headerregistry import Address, HeaderRegistry

STATUS_OK = "ok"
STATUS_LEGACY = "legacy_unquoted"
STATUS_EMPTY = "empty"
STATUS_NO_ADDRESS = "no_address"
STATUS_MULTIPLE = "multiple"
STATUS_INVALID = "invalid"

TRUSTED_STATUSES = frozenset({STATUS_OK, STATUS_LEGACY})

_REGISTRY = HeaderRegistry()
# Forma escrita por los serializadores anteriores: "<texto sin ángulos> <dirección>".
_LEGACY_TRAILING_ANGLE = re.compile(r"^(?P<name>[^<>]*?)\s*<(?P<addr>[^<>]*)>\s*$", re.DOTALL)


@dataclass(frozen=True)
class SenderIdentity:
    display_name: str
    email: str
    status: str

    @property
    def trusted(self) -> bool:
        """La dirección proviene de un análisis no ambiguo (no implica autenticidad)."""
        return bool(self.email) and self.status in TRUSTED_STATUSES

    @property
    def email_lower(self) -> str:
        return self.email.lower() if self.trusted else ""

    @property
    def local_part(self) -> str:
        email = self.email_lower
        return email.rsplit("@", 1)[0] if "@" in email else ""

    @property
    def domain(self) -> str:
        email = self.email_lower
        if "@" not in email:
            return ""
        return email.rsplit("@", 1)[1].strip().rstrip(".")


def _parse_mailboxes(value: str) -> tuple[list[Address], bool]:
    """(direcciones, hubo_defectos) según email.headerregistry; nunca lanza."""
    try:
        header = _REGISTRY("From", value)
    except Exception:  # pragma: no cover - el analizador estándar no debería lanzar
        return [], True
    try:
        addresses = list(header.addresses)
    except Exception:  # pragma: no cover
        return [], True
    return addresses, bool(header.defects)


def _valid_address(address: Address) -> bool:
    username = str(address.username or "")
    domain = str(address.domain or "")
    if not username or not domain:
        return False
    if any(ch.isspace() for ch in domain) or "@" in domain:
        return False
    return True


def _single_address(value: str) -> str:
    """La dirección si ``value`` es exactamente una addr-spec válida; si no, ''."""
    addresses, defects = _parse_mailboxes(value)
    if defects or len(addresses) != 1:
        return ""
    address = addresses[0]
    if address.display_name or not _valid_address(address):
        return ""
    return str(address.addr_spec)


def _display_only(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1].replace('\\"', '"').replace("\\\\", "\\").strip()
    return text


def parse_sender(value: object) -> SenderIdentity:
    """Interpreta un remitente (cabecera From cruda o valor guardado en ``sender``)."""
    raw = str(value or "").strip()
    if not raw:
        return SenderIdentity("", "", STATUS_EMPTY)

    addresses, defects = _parse_mailboxes(raw)
    valid = [a for a in addresses if _valid_address(a)]
    if not defects and len(addresses) == 1 and len(valid) == 1:
        address = valid[0]
        return SenderIdentity(str(address.display_name or "").strip(), str(address.addr_spec), STATUS_OK)

    legacy = _LEGACY_TRAILING_ANGLE.match(raw)
    if legacy:
        email = _single_address(legacy.group("addr").strip())
        if email:
            return SenderIdentity(_display_only(legacy.group("name")), email, STATUS_LEGACY)

    if len(valid) > 1:
        return SenderIdentity(_display_only(raw), "", STATUS_MULTIPLE)
    if not valid and addresses and not any("@" in str(a.addr_spec or "") and a.domain for a in addresses):
        return SenderIdentity(_display_only(raw), "", STATUS_NO_ADDRESS)
    return SenderIdentity(_display_only(raw), "", STATUS_INVALID)


def _decoded_display(raw: str) -> str:
    """Texto legible (encoded-words decodificadas) para un campo sin dirección fiable."""
    try:
        from email.header import decode_header, make_header

        return _display_only(str(make_header(decode_header(raw))))
    except Exception:
        return _display_only(raw)


def format_sender(display_name: str | None, email: str | None) -> str:
    """Serializa nombre y dirección en una cadena RFC 5322 sin ambigüedad.

    - Con dirección válida: ``"Nombre, con coma" <dir@dominio>`` (comillas solo si
      hacen falta; Unicode se conserva legible, RFC 6532).
    - Sin dirección válida: el nombre como texto entre comillas si contiene
      caracteres que podrían leerse como dirección, de modo que al reanalizarlo
      nunca produzca una dirección.
    """
    name = re.sub(r"[\r\n\t]+", " ", str(display_name or "")).strip()
    address = _single_address(str(email or "").strip())
    if address:
        try:
            rendered = str(Address(display_name=name, addr_spec=address))
        except Exception:
            rendered = str(Address(addr_spec=address))
        if parse_sender(rendered).email == address:
            return rendered
        return str(Address(addr_spec=address))
    if not name:
        return ""
    if parse_sender(name).email or re.search(r'[@<>,;:"\\()\[\]]', name):
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return name


def canonical_sender(value: object) -> str:
    """Cabecera From (cruda o decodificada) → cadena canónica para ``sender``."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    identity = parse_sender(raw)
    if identity.trusted:
        return format_sender(identity.display_name, identity.email)
    return format_sender(_decoded_display(raw), "")
