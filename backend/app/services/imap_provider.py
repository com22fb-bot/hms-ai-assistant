"""Configuración IMAP por proveedor. El protocolo es el mismo; el acceso no."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AuthMode = Literal["password", "oauthbearer"]


@dataclass(frozen=True)
class ImapProviderConfig:
    """Servidor y dominios de un buzón IMAP de solo lectura."""

    provider_id: str
    label: str
    host: str
    port: int
    domains: tuple[str, ...]
    auth_mode: AuthMode


YAHOO_IMAP = ImapProviderConfig(
    provider_id="yahoo",
    label="Yahoo",
    host="imap.mail.yahoo.com",
    port=993,
    domains=(),
    auth_mode="oauthbearer",
)

ICLOUD_IMAP = ImapProviderConfig(
    provider_id="icloud",
    label="iCloud",
    host="imap.mail.me.com",
    port=993,
    domains=("icloud.com", "me.com", "mac.com"),
    auth_mode="password",
)

GMAIL_IMAP = ImapProviderConfig(
    provider_id="gmail_imap",
    label="Gmail",
    host="imap.gmail.com",
    port=993,
    # Gmail y Google Workspace (dominio propio): no se restringe por dominio.
    domains=(),
    auth_mode="password",
)

# Proveedores IMAP con contraseña de aplicación que comparten el pipeline de iCloud.
APP_PASSWORD_IMAP_PROVIDERS = ("icloud", "gmail_imap")


# Lectura que no marca el mensaje como leído.
PEEK_HEADER_SPEC = "(FLAGS BODY.PEEK[HEADER])"
PEEK_FULL_SPEC = "(FLAGS BODY.PEEK[])"
