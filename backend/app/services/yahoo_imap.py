"""Lectura de Yahoo Mail por IMAP con OAuth (el usuario firma en Yahoo)."""

from __future__ import annotations

import email
import imaplib
import re
import socket
from datetime import datetime, timezone
from typing import Any

from app.services.imap_mail import (
    ImapMailError,
    decode_header_value,
    list_inbox_messages,
    open_imap_client,
)
from app.services.imap_provider import YAHOO_IMAP
from app.services.yahoo_domains import is_yahoo_mail_address

YAHOO_IMAP_HOST = YAHOO_IMAP.host
YAHOO_IMAP_PORT = YAHOO_IMAP.port


class YahooImapError(ImapMailError):
    """Fallo al conectar o leer Yahoo IMAP."""

    def __init__(self, message: str = "", *, code: str = "imap_failed") -> None:
        super().__init__(message, code=code)


def _yahoo_auth(stored: dict[str, Any] | None) -> str:
    if not stored:
        return ""
    metadata = stored.get("metadata") or {}
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("auth") or "").lower()


def stored_yahoo_uses_oauth(stored: dict[str, Any] | None) -> bool:
    return _yahoo_auth(stored) in {"oauthbearer", "oauth", "oauth2"}


def stored_yahoo_uses_app_password(stored: dict[str, Any] | None) -> bool:
    return _yahoo_auth(stored) == "app_password"


def yahoo_imap_access(
    stored: dict[str, Any] | None,
    email: str,
) -> tuple[str, str, bool]:
    """Devuelve correo, secreto y si el secreto es un token OAuth."""
    token = str((stored or {}).get("access_token") or "")
    address = (email or "").strip()
    if address and token and stored_yahoo_uses_app_password(stored):
        return address, token, False
    if address and token and stored_yahoo_uses_oauth(stored):
        return address, token, True
    raise YahooImapError(
        "Vuelve a conectar Yahoo con una contraseña de app. "
        "La autorización oficial de lectura (mail-r) sigue pendiente.",
        code="yahoo_credentials_missing",
    )


def looks_like_yahoo_app_password(raw: str) -> bool:
    compact = re.sub(r"[\s-]+", "", (raw or "").strip())
    return bool(re.fullmatch(r"[A-Za-z0-9]{16}", compact))


def _decode_header_value(value: str | None) -> str:
    return decode_header_value(value)


def normalize_yahoo_address(address: str) -> str:
    return address.strip().lower()


def normalize_yahoo_app_password(raw: str) -> str:
    """
    Clave IMAP de Yahoo.

    La clave normal se respeta tal cual (símbolos, guiones, espacios).
    Solo se quitan espacios si el resto son exactamente 16 letras o
    números — el formato clásico de un código de aplicación.
    """
    cleaned = (raw or "").strip().replace("\u00a0", " ")
    no_spaces = re.sub(r"\s+", "", cleaned)
    if re.fullmatch(r"[A-Za-z0-9]{16}", no_spaces):
        return no_spaces
    return cleaned


def _is_yahoo_like_address(address: str) -> bool:
    return is_yahoo_mail_address(address)


_YAHOO_OAUTH_BLOCKED = (
    "Donexto aún no puede leer este buzón Yahoo con el permiso oficial. "
    "Falta el alcance mail-r que Yahoo aprueba en la app. "
    "Mientras tanto puedes conectar con una contraseña de app."
)
_YAHOO_WRONG = (
    "Yahoo no aceptó esa contraseña de app. "
    "Revísala o genera otra en la seguridad de la cuenta Yahoo."
)
_YAHOO_APP = (
    "Yahoo no acepta la contraseña de la cuenta. "
    "Donexto usa una contraseña de app: Seguridad de la cuenta Yahoo "
    "> Generar contraseña de app."
)
_YAHOO_ADDRESS = (
    "Indica un correo de Yahoo (@yahoo.com, @yahoo.com.mx, "
    "@ymail.com, @rocketmail.com o similar)."
)
_YAHOO_NETWORK = (
    "No hubo respuesta de Yahoo (imap.mail.yahoo.com:993). "
    "Revisa la red e inténtalo de nuevo."
)


def classify_yahoo_app_error(error_text: str, submitted: str) -> YahooImapError:
    """Traduce el rechazo de Yahoo a un error que se puede seguir."""
    from app.services.imap_mail import scrub_secret

    text = scrub_secret(error_text or "", submitted).lower()
    if any(
        token in text
        for token in (
            "app password",
            "application password",
            "app-specific",
            "generated password",
        )
    ):
        return YahooImapError(_YAHOO_APP, code="app_password_required")
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
        if looks_like_yahoo_app_password(submitted):
            return YahooImapError(_YAHOO_WRONG, code="wrong_password")
        return YahooImapError(_YAHOO_APP, code="app_password_required")
    return YahooImapError(
        scrub_secret(
            f"Yahoo IMAP no pudo autenticar. {error_text}".strip(),
            submitted,
        ),
        code="imap_failed",
    )


def _open_yahoo_client(
    address: str,
    app_password: str,
    *,
    timeout: int = 45,
    oauth: bool = False,
) -> imaplib.IMAP4_SSL:
    try:
        return open_imap_client(
            YAHOO_IMAP,
            address,
            app_password,
            timeout=timeout,
            oauth=oauth,
        )
    except ImapMailError as error:
        if error.code == "network":
            raise YahooImapError(_YAHOO_NETWORK, code="network") from error
        if oauth or error.code == "oauth_rejected":
            raise YahooImapError(_YAHOO_OAUTH_BLOCKED, code="oauth_rejected") from error
        raise classify_yahoo_app_error(str(error), app_password) from error
    except imaplib.IMAP4.error as error:
        raise classify_yahoo_app_error(str(error), app_password) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise YahooImapError(_YAHOO_NETWORK, code="network") from error


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Legacy: IMAP LOGIN. El producto ya no pide claves; no lo usa la API."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)

    if not address or "@" not in address:
        raise YahooImapError("El correo de Yahoo no es válido.")

    if not _is_yahoo_like_address(address):
        raise YahooImapError(_YAHOO_ADDRESS, code="invalid_address")

    if len(app_password) < 8:
        raise YahooImapError(_YAHOO_APP, code="app_password_required")

    try:
        client = _open_yahoo_client(address, app_password)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise YahooImapError(
                    "La contraseña es válida, pero no se pudo abrir el INBOX. "
                    "Revisa la cuenta Yahoo e inténtalo de nuevo."
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except YahooImapError:
        raise
    except imaplib.IMAP4.error as error:
        raise classify_yahoo_app_error(str(error), app_password) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise YahooImapError(_YAHOO_NETWORK, code="network") from error
    except Exception as error:
        raise YahooImapError(
            f"Error al conectar con Yahoo IMAP: {error}"
        ) from error


def verify_yahoo_app_login(address: str, app_password: str) -> str:
    """LOGIN real y EXAMINE del INBOX. Devuelve el correo normalizado."""
    verify_yahoo_login(address, app_password)
    return normalize_yahoo_address(address)


def list_yahoo_messages(
    address: str,
    app_password: str,
    *,
    max_results: int = 20,
    oauth: bool = False,
) -> list[dict[str, Any]]:
    """Lista mensajes recientes del INBOX de Yahoo. Solo lectura."""
    address = normalize_yahoo_address(address)
    if not oauth:
        app_password = normalize_yahoo_app_password(app_password)
    try:
        return list_inbox_messages(
            YAHOO_IMAP,
            address,
            app_password,
            max_results=max_results,
            oauth=oauth,
            labels=["YAHOO", "INBOX"],
        )
    except YahooImapError:
        raise
    except ImapMailError as error:
        if error.code == "network":
            raise YahooImapError(_YAHOO_NETWORK, code="network") from error
        if oauth or error.code == "oauth_rejected":
            raise YahooImapError(_YAHOO_OAUTH_BLOCKED, code="oauth_rejected") from error
        raise classify_yahoo_app_error(str(error), app_password) from error
    except imaplib.IMAP4.error as error:
        raise classify_yahoo_app_error(str(error), app_password) from error
    except Exception as error:
        raise YahooImapError(
            f"No fue posible leer correos de Yahoo: {error}"
        ) from error


IMAP_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

INBOX_ALIASES = {"inbox"}
SENT_ALIASES = {
    "sent",
    "sent mail",
    "sent messages",
    "sent items",
    "enviados",
    "envoyés",
    "envoyes",
    "messages envoyés",
    "messages envoyes",
    "inviati",
    "posta inviata",
    "gesendet",
    "enviadas",
}
DRAFT_ALIASES = {
    "draft",
    "drafts",
    "borradores",
    "brouillons",
    "bozze",
    "rascunhos",
    "entwürfe",
    "entwurfe",
}
SPAM_ALIASES = {
    "bulk mail",
    "junk",
    "junk mail",
    "spam",
    "correo no deseado",
    "indésirables",
    "indesirables",
    "courrier indésirable",
    "courrier indesirable",
    "posta indesiderata",
    "lixo",
    "lixo eletrônico",
    "lixo eletronico",
}
TRASH_ALIASES = {
    "trash",
    "deleted",
    "deleted items",
    "deleted messages",
    "deleted message",
    "papelera",
    "eliminados",
    "corbeille",
    "cestino",
    "lixeira",
    "papierkorb",
    "bin",
}

_SPECIAL_USE = (
    ("\\trash", "trash"),
    ("\\junk", "spam"),
    ("\\spam", "spam"),
    ("\\drafts", "draft"),
    ("\\sent", "sent"),
    ("\\inbox", "inbox"),
)


def imap_search_date(value: datetime) -> str:
    current = value.astimezone(timezone.utc) if value.tzinfo else value.replace(
        tzinfo=timezone.utc
    )
    return f"{current.day:02d}-{IMAP_MONTHS[current.month - 1]}-{current.year}"


def classify_yahoo_folder(name: str, flags: str = "") -> str:
    """Carpeta por atributo IMAP (\\Sent, \\Trash) y, si no hay, por el nombre.

    iCloud en inglés llama a la papelera ``Deleted Messages``. Apple y
    otros servidores traducen Enviados (Envoyés, Inviati, Enviados).
    """
    lowered_flags = f" {(flags or '').lower()} "
    for token, role in _SPECIAL_USE:
        if token in lowered_flags:
            return role
    lowered = name.strip().lower().strip('"')
    leaf = lowered.rsplit("/", 1)[-1].rsplit(".", 1)[-1]
    if leaf in INBOX_ALIASES or lowered in INBOX_ALIASES:
        return "inbox"
    if leaf in SENT_ALIASES or lowered in SENT_ALIASES:
        return "sent"
    if leaf in DRAFT_ALIASES or lowered in DRAFT_ALIASES:
        return "draft"
    if leaf in SPAM_ALIASES or lowered in SPAM_ALIASES:
        return "spam"
    if leaf in TRASH_ALIASES or lowered in TRASH_ALIASES:
        return "trash"
    return "other"


def parse_list_mailbox_flags(raw: bytes | str) -> str:
    text = (
        raw.decode("utf-8", errors="ignore")
        if isinstance(raw, bytes)
        else str(raw)
    ).strip()
    matched = re.match(r"^\(([^)]*)\)", text)
    return matched.group(1) if matched else ""


def parse_list_mailbox_name(raw: bytes | str) -> str | None:
    text = (
        raw.decode("utf-8", errors="ignore")
        if isinstance(raw, bytes)
        else str(raw)
    ).strip()
    if not text:
        return None
    quoted = re.findall(r'"((?:\\.|[^"\\])*)"', text)
    if quoted:
        return quoted[-1].replace('\\"', '"')
    parts = text.split()
    return parts[-1] if parts else None


def encode_yahoo_ref(folder: str, uid: str) -> str:
    return f"{folder}\x1f{uid}"


def decode_yahoo_ref(ref: str) -> tuple[str, str]:
    if "\x1f" in ref:
        folder, uid = ref.split("\x1f", 1)
        return folder, uid
    if ":" in ref:
        folder, uid = ref.split(":", 1)
        return folder, uid
    return "INBOX", ref


def extract_rfc822_bodies(parsed: email.message.Message) -> tuple[str, str, bool]:
    text = ""
    html = ""
    has_attachments = False

    if parsed.is_multipart():
        for part in parsed.walk():
            disposition = str(part.get("Content-Disposition") or "").lower()
            content_type = part.get_content_type()
            if "attachment" in disposition:
                has_attachments = True
                continue
            payload = part.get_payload(decode=True)
            if not isinstance(payload, (bytes, bytearray)):
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain" and not text:
                text = decoded
            elif content_type == "text/html" and not html:
                html = decoded
        return text, html, has_attachments

    payload = parsed.get_payload(decode=True)
    charset = parsed.get_content_charset() or "utf-8"
    if isinstance(payload, (bytes, bytearray)):
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("utf-8", errors="replace")
        if parsed.get_content_type() == "text/html":
            html = decoded
        else:
            text = decoded
    return text, html, has_attachments
