"""Gmail por IMAP, solo lectura, con contraseña de aplicación de Google.

Alternativa a OAuth (sin verificación CASA). Requiere la verificación en dos
pasos activa y una contraseña de aplicación (myaccount.google.com/apppasswords),
distinta de la contraseña de Google.

Host: imap.gmail.com:993 SSL. Usuario: el correo completo.
La contraseña nunca se registra; los errores pasan por ``scrub_secret``.
"""

from __future__ import annotations

import imaplib
import re
import socket
from typing import Any

from app.services.imap_mail import (
    ImapMailError,
    examine_mailbox,
    list_inbox_messages,
    normalize_imap_address,
    open_imap_client,
    scrub_secret,
)
from app.services.icloud_imap import IcloudImapError
from app.services.imap_provider import GMAIL_IMAP


class GmailImapError(IcloudImapError):
    """Fallo claro al conectar o leer Gmail por IMAP.

    Hereda de ``IcloudImapError`` para que el pipeline de contraseña de app
    (importación guiada, sync) lo trate igual que iCloud.
    """


_APP_PASSWORD = re.compile(r"^[A-Za-z]{16}$")

_MSG_WRONG = (
    "Gmail no aceptó esa contraseña de aplicación. "
    "Revísala o crea otra en myaccount.google.com/apppasswords."
)
_MSG_APP = (
    "Gmail no acepta tu contraseña normal de Google. Usa una contraseña de "
    "aplicación de 16 letras (myaccount.google.com/apppasswords). "
    "Para crearla necesitas la verificación en dos pasos activa."
)
_MSG_IMAP_OFF = (
    "Gmail tiene el acceso IMAP desactivado para esta cuenta. "
    "Si es de trabajo o escuela, pide al administrador que lo active."
)
_MSG_ADDRESS = "Indica el correo completo de Gmail."
_MSG_NETWORK = (
    "No hubo respuesta de Gmail (imap.gmail.com:993). "
    "Revisa la red e inténtalo de nuevo."
)


def normalize_gmail_address(address: str) -> str:
    return normalize_imap_address(address)


def normalize_gmail_app_password(raw: str) -> str:
    """Acepta ``abcd efgh ijkl mnop`` (como lo muestra Google) o las 16 letras seguidas."""
    cleaned = (raw or "").strip().replace("\u00a0", "")
    compact = re.sub(r"[\s-]+", "", cleaned)
    if _APP_PASSWORD.fullmatch(compact):
        return compact
    return cleaned


def looks_like_google_app_password(raw: str) -> bool:
    return bool(_APP_PASSWORD.fullmatch(re.sub(r"[\s-]+", "", (raw or "").strip())))


def classify_gmail_auth_error(error_text: str, submitted: str) -> GmailImapError:
    text = scrub_secret(error_text or "", submitted).lower()
    if "application-specific password" in text or "app password" in text or "webloginrequired" in text:
        return GmailImapError(_MSG_APP, code="app_password_required")
    if "imap access is disabled" in text or "imap is disabled" in text or "not enabled for imap" in text:
        return GmailImapError(_MSG_IMAP_OFF, code="imap_disabled")
    if any(t in text for t in ("invalid credentials", "authenticationfailed", "authentication failed", "login failed", "credentials")):
        if looks_like_google_app_password(submitted):
            return GmailImapError(_MSG_WRONG, code="wrong_password")
        return GmailImapError(_MSG_APP, code="app_password_required")
    return GmailImapError(
        scrub_secret(f"Gmail IMAP no pudo autenticar. {error_text}".strip(), submitted),
        code="imap_failed",
    )


def _validate_pair(address: str, app_password: str) -> tuple[str, str]:
    address = normalize_gmail_address(address)
    app_password = normalize_gmail_app_password(app_password)
    if not address or "@" not in address or "." not in address.rsplit("@", 1)[-1]:
        raise GmailImapError(_MSG_ADDRESS, code="invalid_address")
    if len(app_password) < 8:
        raise GmailImapError(_MSG_APP, code="app_password_required")
    return address, app_password


def open_gmail_imap_client(address: str, app_password: str, *, timeout: int = 45) -> imaplib.IMAP4_SSL:
    address, app_password = _validate_pair(address, app_password)
    try:
        return open_imap_client(GMAIL_IMAP, address, app_password, timeout=timeout, oauth=False)
    except GmailImapError:
        raise
    except ImapMailError as error:
        if error.code == "network":
            raise GmailImapError(_MSG_NETWORK, code="network") from error
        raise classify_gmail_auth_error(str(error), app_password) from error
    except imaplib.IMAP4.error as error:
        raise classify_gmail_auth_error(str(error), app_password) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise GmailImapError(_MSG_NETWORK, code="network") from error


def verify_gmail_imap_login(address: str, app_password: str) -> str:
    """LOGIN real + EXAMINE INBOX (solo lectura). Devuelve el correo normalizado."""
    address, app_password = _validate_pair(address, app_password)
    try:
        client = open_gmail_imap_client(address, app_password)
        try:
            examine_mailbox(client, "INBOX")
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except GmailImapError:
        raise
    except ImapMailError as error:
        raise GmailImapError(scrub_secret(str(error), app_password), code=error.code) from error
    except Exception as error:
        raise GmailImapError(
            scrub_secret(f"Error al conectar con Gmail: {error}", app_password),
            code="imap_failed",
        ) from error
    return address


def list_gmail_imap_messages(address: str, app_password: str, *, max_results: int = 20) -> list[dict[str, Any]]:
    address, app_password = _validate_pair(address, app_password)
    try:
        return list_inbox_messages(
            GMAIL_IMAP, address, app_password, max_results=max_results, oauth=False, labels=["GMAIL", "INBOX"],
        )
    except GmailImapError:
        raise
    except imaplib.IMAP4.error as error:
        raise classify_gmail_auth_error(str(error), app_password) from error
    except ImapMailError as error:
        if error.code == "network":
            raise GmailImapError(_MSG_NETWORK, code="network") from error
        if error.code in {"auth_failed", "oauth_rejected"}:
            raise classify_gmail_auth_error(str(error), app_password) from error
        raise GmailImapError(scrub_secret(str(error), app_password), code=error.code) from error
    except Exception as error:
        raise GmailImapError(
            scrub_secret(f"No fue posible leer correos de Gmail: {error}", app_password),
            code="imap_failed",
        ) from error
