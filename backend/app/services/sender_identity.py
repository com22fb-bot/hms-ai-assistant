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
   ``<dirección>``, el texto previo no contiene ``<`` ni ``>`` y el analizador no
   ve ningún OTRO buzón válido (solo fragmentos sin dominio, p. ej. ``Perez``), la
   dirección es la del ``<...>`` final. Es la forma que escribían los
   serializadores anteriores y la dirección entre ángulos es la real (RFC 5322
   name-addr). Si el texto previo contiene otra dirección válida
   (``aviso@banco, Soporte <x@a>``) hay dos identidades y no se elige ninguna.

Analizar bien una dirección NO prueba que el remitente sea auténtico (SPF/DKIM/DMARC
quedan fuera de este módulo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from email import errors as email_errors
from email.headerregistry import Address, HeaderRegistry

STATUS_OK = "ok"
STATUS_LEGACY = "legacy_unquoted"
STATUS_EMPTY = "empty"
STATUS_NO_ADDRESS = "no_address"
STATUS_MULTIPLE = "multiple"
STATUS_INVALID = "invalid"

TRUSTED_STATUSES = frozenset({STATUS_OK, STATUS_LEGACY})

_REGISTRY = HeaderRegistry()
# Defectos que no vuelven ambigua una dirección única: sintaxis obsoleta pero
# interpretable (p. ej. punto en el nombre "Amazon.com", ruta obsoleta) y
# local-part no ASCII (RFC 6531, "josé@dominio"). Cualquier otro defecto
# (InvalidHeaderDefect, etc.) invalida el campo.
_BENIGN_DEFECTS = (email_errors.ObsoleteHeaderDefect, email_errors.NonASCIILocalPartDefect)
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


def _parse_mailboxes(value: str) -> tuple[list[Address], bool, bool]:
    """(direcciones, hubo_defectos_graves, error_de_análisis) según email.headerregistry.

    Nunca lanza. Si el analizador estándar falla (p. ej. sintaxis de grupo seguida
    de otro buzón), ``error_de_análisis`` es True y el campo se trata como
    inválido sin aplicar ninguna regla de compatibilidad (revisión de seguridad #218).
    """
    try:
        header = _REGISTRY("From", value)
        addresses = list(header.addresses)
        defects = list(header.defects)
    except Exception:
        return [], True, True
    fatal = [d for d in defects if not isinstance(d, _BENIGN_DEFECTS)]
    return addresses, bool(fatal), False


def _valid_address(address: Address) -> bool:
    username = str(address.username or "")
    domain = str(address.domain or "")
    if not username or not domain:
        return False
    if any(ch.isspace() for ch in domain) or "@" in domain:
        return False
    return True


def _single_mailbox(value: str) -> Address | None:
    """El ``Address`` si ``value`` es exactamente una addr-spec válida sin nombre."""
    addresses, defects, failed = _parse_mailboxes(value)
    if failed or defects or len(addresses) != 1:
        return None
    address = addresses[0]
    if address.display_name or not _valid_address(address):
        return None
    return address


def _single_address(value: str) -> str:
    """La dirección si ``value`` es exactamente una addr-spec válida; si no, ''."""
    mailbox = _single_mailbox(value)
    return str(mailbox.addr_spec) if mailbox is not None else ""


def _display_only(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1].replace('\\"', '"').replace("\\\\", "\\").strip()
    return text


def parse_sender(value: object) -> SenderIdentity:
    """Interpreta un remitente (cabecera From cruda o valor guardado en ``sender``)."""
    return _parse_sender_text(str(value or "").strip())


@lru_cache(maxsize=4096)
def _parse_sender_text(raw: str) -> SenderIdentity:
    # Resultado inmutable (dataclass frozen): seguro de reutilizar entre llamadas.
    if not raw:
        return SenderIdentity("", "", STATUS_EMPTY)

    addresses, defects, failed = _parse_mailboxes(raw)
    if failed:
        return SenderIdentity(_display_only(raw), "", STATUS_INVALID)
    valid = [a for a in addresses if _valid_address(a)]
    if not defects and len(addresses) == 1 and len(valid) == 1:
        address = valid[0]
        return SenderIdentity(str(address.display_name or "").strip(), str(address.addr_spec), STATUS_OK)

    # Fail-closed: dos o más buzones válidos son varias identidades; no se
    # elige ninguna (ni la primera ni la del <...> final). Va ANTES de la regla
    # de compatibilidad para que "atacante@x, Soporte <aviso@banco>" no
    # produzca una identidad (revisión de seguridad del PR #218).
    if len(valid) > 1:
        return SenderIdentity(_display_only(raw), "", STATUS_MULTIPLE)

    legacy = _LEGACY_TRAILING_ANGLE.match(raw)
    if legacy:
        email = _single_address(legacy.group("addr").strip())
        # El único buzón válido que ve el analizador debe ser el del <...> final;
        # el resto son fragmentos del nombre sin dominio ("Perez", "Banamex").
        # Exige exactamente un buzón válido y que sea ese; sin sintaxis de grupo.
        name_part = legacy.group("name")
        if (email and len(valid) == 1 and str(valid[0].addr_spec) == email
                and ":" not in name_part and ";" not in name_part):
            return SenderIdentity(_display_only(legacy.group("name")), email, STATUS_LEGACY)

    display = _display_only(raw)
    # Sin "@" es solo un nombre; con "@" pero sin dirección utilizable es un
    # campo inválido (incluye lo que se guardó como texto tras rechazar varias
    # identidades), y los consumidores pueden tratarlo con desconfianza.
    if "@" not in display:
        return SenderIdentity(display, "", STATUS_NO_ADDRESS)
    return SenderIdentity(display, "", STATUS_INVALID)


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
    mailbox = _single_mailbox(str(email or "").strip())
    if mailbox is not None:
        address = str(mailbox.addr_spec)
        # username/domain en lugar de addr_spec: Address(addr_spec=...) rechaza
        # local-parts no ASCII (RFC 6531) que el análisis sí acepta.
        username, domain = str(mailbox.username), str(mailbox.domain)
        bare = str(Address(username=username, domain=domain))
        try:
            rendered = str(Address(display_name=name, username=username, domain=domain))
        except Exception:
            rendered = bare
        if parse_sender(rendered).email == address:
            return rendered
        return bare
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
