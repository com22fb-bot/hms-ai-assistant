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
import unicodedata
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

    #: Respuesta del servidor IMAP ya sin el secreto (solo para logs).
    server_text: str = ""


_APP_PASSWORD = re.compile(r"^[A-Za-z]{16}$")

_MSG_WRONG = (
    "Gmail no aceptó esa contraseña de aplicación para este correo. "
    "Créala con la sesión de Google de este mismo correo en "
    "myaccount.google.com/apppasswords."
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
_MSG_WEB_LOGIN = (
    "Google pide confirmar el acceso en el navegador. Entra a tu cuenta de "
    "Google, revisa el aviso de seguridad y vuelve a intentar."
)
_MSG_THROTTLED = "Gmail bloqueó temporalmente los intentos. Espera unos minutos."
_MSG_CHARS = "La contraseña de aplicación solo lleva letras. Cópiala otra vez desde Google."
_MSG_ADDRESS = "Indica el correo completo de Gmail."
_MSG_NETWORK = (
    "No hubo respuesta de Gmail (imap.gmail.com:993). "
    "Revisa la red e inténtalo de nuevo."
)


def normalize_gmail_address(address: str) -> str:
    return normalize_imap_address(address)


def _strip_invisible(raw: str) -> str:
    """Quita todo espacio (incluido Unicode: NBSP, finos, ideográficos) y los
    caracteres invisibles de formato (zero-width, BOM, marcas de dirección)
    que llegan al copiar y pegar. NFKC convierte letras de ancho completo."""
    text = unicodedata.normalize("NFKC", raw or "")
    return "".join(
        ch for ch in text
        if not ch.isspace() and unicodedata.category(ch) not in {"Cf", "Zs", "Zl", "Zp", "Cc"}
    )


def normalize_gmail_app_password(raw: str) -> str:
    """Google muestra ``abcd efgh ijkl mnop``; Gmail espera las 16 letras sin espacios.

    La contraseña de aplicación nunca lleva espacios, así que se quitan siempre
    (antes solo se quitaban si el resultado eran 16 letras exactas; si no, se
    enviaba el texto con espacios). No se cambia mayúsculas/minúsculas.
    """
    compact = _strip_invisible(raw)
    without_hyphens = compact.replace("-", "")
    if _APP_PASSWORD.fullmatch(without_hyphens):
        return without_hyphens
    return compact


def looks_like_google_app_password(raw: str) -> bool:
    return bool(_APP_PASSWORD.fullmatch(_strip_invisible(raw).replace("-", "")))


def classify_gmail_auth_error(error_text: str, submitted: str) -> GmailImapError:
    server = scrub_secret(error_text or "", submitted)
    error = _classify(server.lower(), submitted)
    error.server_text = server[:300]
    return error


def _classify(text: str, submitted: str) -> GmailImapError:
    if "application-specific password" in text or "app password" in text:
        return GmailImapError(_MSG_APP, code="app_password_required")
    if "webloginrequired" in text or "web browser" in text or "web login" in text:
        return GmailImapError(_MSG_WEB_LOGIN, code="web_login_required")
    if "too many" in text or ("rate" in text and "limit" in text):
        return GmailImapError(_MSG_THROTTLED, code="rate_limited")
    if "imap access is disabled" in text or "imap is disabled" in text or "not enabled for imap" in text:
        return GmailImapError(_MSG_IMAP_OFF, code="imap_disabled")
    if any(t in text for t in ("invalid credentials", "authenticationfailed", "authentication failed", "login failed", "credentials")):
        if looks_like_google_app_password(submitted):
            return GmailImapError(_MSG_WRONG, code="wrong_password")
        return GmailImapError(_MSG_APP, code="app_password_required")
    return GmailImapError(
        scrub_secret("Gmail IMAP no pudo autenticar.", submitted),
        code="imap_failed",
    )


def _validate_pair(address: str, app_password: str) -> tuple[str, str]:
    address = normalize_gmail_address(address)
    app_password = normalize_gmail_app_password(app_password)
    if not address or "@" not in address or "." not in address.rsplit("@", 1)[-1]:
        raise GmailImapError(_MSG_ADDRESS, code="invalid_address")
    if len(app_password) < 8:
        raise GmailImapError(_MSG_APP, code="app_password_required")
    if not app_password.isascii():
        # imaplib solo envía ASCII; un carácter raro rompería el LOGIN.
        raise GmailImapError(_MSG_CHARS, code="invalid_characters")
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
