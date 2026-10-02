"""iCloud Mail por IMAP, solo lectura, con contraseña específica de app.

Apple no entrega un alcance OAuth de correo a Donexto. El acceso
autorizado es una contraseña de app (account.apple.com), distinta de
la contraseña del Apple ID. Hace falta la verificación en dos pasos
para generarla.

Host: imap.mail.me.com:993 SSL.
Usuario: el correo completo (@icloud.com, @me.com o @mac.com).
"""

from __future__ import annotations

import imaplib
import re
import socket
from typing import Any

from app.services.imap_mail import (
    ImapMailError,
    address_matches,
    examine_mailbox,
    list_inbox_messages,
    normalize_imap_address,
    open_imap_client,
    scrub_secret,
)
from app.services.imap_provider import ICLOUD_IMAP


class IcloudImapError(ImapMailError):
    """Fallo claro al conectar o leer iCloud."""


_APP_PASSWORD = re.compile(r"^[A-Za-z0-9]{16}$")

_MSG_WRONG = (
    "iCloud no aceptó esa contraseña específica de app. "
    "Revísala o genera otra en account.apple.com."
)
_MSG_APP = (
    "iCloud no acepta la contraseña del Apple ID. "
    "Donexto solo usa una contraseña específica de app. "
    "Para crearla necesitas la verificación en dos pasos activa, "
    "en account.apple.com > Inicio de sesión y seguridad > "
    "Contraseñas específicas de app."
)
_MSG_2FA = (
    "La cuenta Apple necesita la verificación en dos pasos "
    "para permitir el acceso de Donexto. Actívala en "
    "account.apple.com, crea una contraseña específica de app "
    "y vuelve a intentar."
)
_MSG_ADDRESS = (
    "Indica el correo completo de iCloud "
    "(@icloud.com, @me.com o @mac.com)."
)
_MSG_NETWORK = (
    "No hubo respuesta de iCloud (imap.mail.me.com:993). "
    "Revisa la red e inténtalo de nuevo."
)


def normalize_icloud_address(address: str) -> str:
    return normalize_imap_address(address)


def normalize_icloud_app_password(raw: str) -> str:
    """Acepta `xxxx-xxxx-xxxx-xxxx` o las 16 letras/números seguidos."""
    cleaned = (raw or "").strip().replace("\u00a0", "")
    compact = re.sub(r"[\s-]+", "", cleaned)
    if _APP_PASSWORD.fullmatch(compact):
        return compact
    return cleaned


def looks_like_apple_app_password(raw: str) -> bool:
    compact = re.sub(r"[\s-]+", "", (raw or "").strip())
    return bool(_APP_PASSWORD.fullmatch(compact))


def is_icloud_address(address: str) -> bool:
    return address_matches(ICLOUD_IMAP, address)


def classify_icloud_auth_error(error_text: str, submitted: str) -> IcloudImapError:
    """Traduce el rechazo de Apple a un error que el usuario puede seguir."""
    text = scrub_secret(error_text or "", submitted).lower()
    if any(
        token in text
        for token in (
            "two-factor",
            "two factor",
            "2fa",
            "two-step",
            "two step",
            "2-step",
            "verification code",
            "web browser",
            "appleid.apple.com",
            "please log in",
        )
    ):
        return IcloudImapError(_MSG_2FA, code="two_factor_required")
    if any(
        token in text
        for token in (
            "app-specific",
            "application-specific",
            "application specific",
            "app specific",
            "app password",
        )
    ):
        return IcloudImapError(_MSG_APP, code="app_password_required")
    if any(
        token in text
        for token in (
            "invalid",
            "authenticationfailed",
            "authentication failed",
            "auth failed",
            "login failed",
            "authenticate",
            "credentials",
        )
    ):
        if looks_like_apple_app_password(submitted):
            return IcloudImapError(_MSG_WRONG, code="wrong_password")
        return IcloudImapError(_MSG_APP, code="app_password_required")
    return IcloudImapError(
        scrub_secret(
            f"iCloud IMAP no pudo autenticar. {error_text}".strip(),
            submitted,
        ),
        code="imap_failed",
    )


def _validate_pair(address: str, app_password: str) -> tuple[str, str]:
    address = normalize_icloud_address(address)
    app_password = normalize_icloud_app_password(app_password)
    if not address or "@" not in address or not is_icloud_address(address):
        raise IcloudImapError(_MSG_ADDRESS, code="invalid_address")
    if len(app_password) < 8:
        raise IcloudImapError(_MSG_APP, code="app_password_required")
    return address, app_password


def open_icloud_client(
    address: str,
    app_password: str,
    *,
    timeout: int = 45,
) -> imaplib.IMAP4_SSL:
    address, app_password = _validate_pair(address, app_password)
    try:
        return open_imap_client(
            ICLOUD_IMAP,
            address,
            app_password,
            timeout=timeout,
            oauth=False,
        )
    except IcloudImapError:
        raise
    except ImapMailError as error:
        if error.code == "network":
            raise IcloudImapError(_MSG_NETWORK, code="network") from error
        raise classify_icloud_auth_error(str(error), app_password) from error
    except imaplib.IMAP4.error as error:
        raise classify_icloud_auth_error(str(error), app_password) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise IcloudImapError(
            _MSG_NETWORK,
            code="network",
        ) from error


def verify_icloud_login(address: str, app_password: str) -> str:
    """LOGIN real y EXAMINE del INBOX. Devuelve el correo normalizado.

    No deja el buzón abierto y no cambia flags.
    """
    address, app_password = _validate_pair(address, app_password)
    try:
        client = open_icloud_client(address, app_password)
        try:
            examine_mailbox(client, "INBOX")
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except IcloudImapError:
        raise
    except ImapMailError as error:
        raise IcloudImapError(str(error), code=error.code) from error
    except Exception as error:
        raise IcloudImapError(
            scrub_secret(f"Error al conectar con iCloud: {error}", app_password),
            code="imap_failed",
        ) from error
    return address


def list_icloud_messages(
    address: str,
    app_password: str,
    *,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    address, app_password = _validate_pair(address, app_password)
    try:
        return list_inbox_messages(
            ICLOUD_IMAP,
            address,
            app_password,
            max_results=max_results,
            oauth=False,
            labels=["ICLOUD", "INBOX"],
        )
    except IcloudImapError:
        raise
    except imaplib.IMAP4.error as error:
        raise classify_icloud_auth_error(str(error), app_password) from error
    except ImapMailError as error:
        if error.code == "network":
            raise IcloudImapError(_MSG_NETWORK, code="network") from error
        if error.code in {"auth_failed", "oauth_rejected"}:
            raise classify_icloud_auth_error(str(error), app_password) from error
        raise IcloudImapError(
            scrub_secret(str(error), app_password),
            code=error.code,
        ) from error
    except Exception as error:
        raise IcloudImapError(
            scrub_secret(
                f"No fue posible leer correos de iCloud: {error}",
                app_password,
            ),
            code="imap_failed",
        ) from error


def stored_icloud_uses_app_password(stored: dict[str, Any] | None) -> bool:
    if not stored:
        return False
    metadata = stored.get("metadata") or {}
    if not isinstance(metadata, dict):
        return False
    return str(metadata.get("auth") or "").lower() == "app_password"
