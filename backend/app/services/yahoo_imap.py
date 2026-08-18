"""Lectura de Yahoo Mail por IMAP (contraseña de aplicación)."""

from __future__ import annotations

import email
import imaplib
import ipaddress
import re
import socket
import ssl
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any


YAHOO_IMAP_HOST = "imap.mail.yahoo.com"
YAHOO_IMAP_PORT = 993
YAHOO_DOMAINS = (
    "yahoo.com",
    "yahoo.com.mx",
    "yahoo.es",
    "ymail.com",
    "rocketmail.com",
)
AOL_DOMAINS = (
    "aol.com",
    "aim.com",
)
OUTLOOK_DOMAINS = (
    "outlook.com",
    "outlook.es",
    "hotmail.com",
    "hotmail.es",
    "live.com",
    "msn.com",
)
APPLE_DOMAINS = (
    "icloud.com",
    "me.com",
    "mac.com",
)
IMAP_BRANDS = {
    "yahoo": {
        "host": "imap.mail.yahoo.com",
        "label": "Yahoo",
        "domains": YAHOO_DOMAINS,
        "allow_any_domain": False,
    },
    "aol": {
        "host": "imap.aol.com",
        "label": "AOL",
        "domains": AOL_DOMAINS,
        "allow_any_domain": False,
    },
    "outlook": {
        "host": "outlook.office365.com",
        "label": "Outlook / Microsoft 365",
        "domains": OUTLOOK_DOMAINS,
        # Hotmail/Outlook.com y también tu@empresa.com en Microsoft 365.
        "allow_any_domain": True,
    },
    "apple": {
        "host": "imap.mail.me.com",
        "label": "iCloud",
        "domains": APPLE_DOMAINS,
        # iCloud+ con dominio propio.
        "allow_any_domain": True,
    },
    "company": {
        "host": "",
        "label": "Empresa",
        "domains": (),
        "allow_any_domain": True,
    },
}


class YahooImapError(RuntimeError):
    """Fallo al conectar o leer Yahoo IMAP."""


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def normalize_yahoo_address(address: str) -> str:
    return address.strip().lower()


def normalize_yahoo_app_password(raw: str) -> str:
    """
    Normaliza contraseña de aplicación Yahoo.

    Yahoo genera ~16 caracteres alfanuméricos (a veces con espacios).
    El gestor de contraseñas a veces pega guiones o textos extra.
    """
    cleaned = raw.strip()
    # Quita etiquetas tipo "App password: "
    cleaned = re.sub(
        r"(?i)^(?:app\s*password|contrase[nñ]a(?:\s+de\s+aplicaci[oó]n)?)\s*[:=]?\s*",
        "",
        cleaned,
    ).strip()
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("-", " ").replace(".", " ")
    cleaned = re.sub(r"\s+", "", cleaned)
    # Solo caracteres alfanuméricos típicos de app password
    alnum = re.sub(r"[^A-Za-z0-9]", "", cleaned)
    if len(alnum) >= 12:
        return alnum
    return cleaned


def _domain_matches(address: str, roots: tuple[str, ...]) -> bool:
    if "@" not in address:
        return False
    domain = address.rsplit("@", 1)[-1]
    return any(
        domain == item or domain.endswith("." + item)
        for item in roots
    )


def _is_yahoo_like_address(address: str) -> bool:
    return _domain_matches(address, YAHOO_DOMAINS) or _domain_matches(
        address, AOL_DOMAINS
    )


def normalize_imap_brand(brand: str, address: str = "") -> str:
    value = (brand or "yahoo").strip().lower()
    if value in {"hotmail", "microsoft", "live", "office", "o365", "m365"}:
        value = "outlook"
    if value in {"icloud", "me", "mac"}:
        value = "apple"
    if value in {"empresa", "work", "custom", "imap", "domain"}:
        value = "company"
    if value == "yahoo" and address and _domain_matches(address, AOL_DOMAINS):
        return "aol"
    if value == "aol":
        return "aol"
    return value if value in IMAP_BRANDS else ""


def safe_imap_host(raw: str | None) -> str:
    """Host IMAP público en 993. Rechaza IPs privadas y localhost."""
    cleaned = (raw or "").strip().lower()
    cleaned = cleaned.replace("imap://", "").replace("imaps://", "")
    cleaned = cleaned.replace("https://", "").replace("http://", "")
    cleaned = cleaned.split("/")[0].strip().rstrip(".")
    if not cleaned:
        raise YahooImapError(
            "Indica el servidor IMAP de tu empresa (por ejemplo imap.tudominio.com)."
        )
    if cleaned.startswith("[") and "]" in cleaned:
        raise YahooImapError("Usa el nombre del servidor IMAP, no una dirección IP.")
    if ":" in cleaned:
        name, port = cleaned.rsplit(":", 1)
        if port.isdigit():
            if int(port) != YAHOO_IMAP_PORT:
                raise YahooImapError("Solo IMAP con TLS en el puerto 993.")
            cleaned = name
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", cleaned):
        raise YahooImapError("Usa el nombre del servidor IMAP, no una dirección IP.")
    if not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
        cleaned,
    ):
        raise YahooImapError("El servidor IMAP no es un nombre de host válido.")
    if cleaned in {"localhost", "localhost.localdomain"} or cleaned.endswith(".local"):
        raise YahooImapError("Ese servidor IMAP no está permitido.")
    try:
        infos = socket.getaddrinfo(cleaned, YAHOO_IMAP_PORT, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise YahooImapError(
            f"No se resolvió el servidor IMAP {cleaned}."
        ) from error
    for info in infos:
        ip_text = str(info[4][0])
        try:
            parsed = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_reserved
            or parsed.is_unspecified
        ):
            raise YahooImapError(
                "El servidor IMAP de la empresa debe ser un host público."
            )
    return cleaned


def assert_address_allowed_for_brand(address: str, brand: str) -> None:
    profile = IMAP_BRANDS.get(brand)
    if not profile:
        raise YahooImapError("Ese proveedor de correo no está activo.")
    label = str(profile["label"])
    if not address or "@" not in address:
        raise YahooImapError(f"El correo de {label} no es válido.")
    if profile.get("allow_any_domain"):
        return
    domains = tuple(profile.get("domains") or ())
    if not _domain_matches(address, domains):
        examples = ", ".join("@" + item for item in domains[:4])
        raise YahooImapError(f"Indica un correo de {label} ({examples}).")


def imap_host_for(brand: str, stored: dict[str, Any] | None = None) -> str:
    meta = (stored or {}).get("metadata") or {}
    host = str(meta.get("host") or "").strip()
    if host:
        return host
    profile = IMAP_BRANDS.get(brand) or IMAP_BRANDS["yahoo"]
    return str(profile["host"])


def _open_yahoo_client(
    address: str,
    app_password: str,
    *,
    timeout: int = 45,
    host: str | None = None,
) -> imaplib.IMAP4_SSL:
    context = ssl.create_default_context()
    safe_timeout = max(15, int(timeout))
    imap_host = (host or YAHOO_IMAP_HOST).strip() or YAHOO_IMAP_HOST
    try:
        client = imaplib.IMAP4_SSL(
            imap_host,
            YAHOO_IMAP_PORT,
            ssl_context=context,
            timeout=safe_timeout,
        )
    except TypeError:
        # Python sin soporte timeout en este build
        socket.setdefaulttimeout(safe_timeout)
        client = imaplib.IMAP4_SSL(
            imap_host,
            YAHOO_IMAP_PORT,
            ssl_context=context,
        )

    status, data = client.login(address, app_password)
    if status != "OK":
        try:
            client.logout()
        except Exception:
            pass
        detail = ""
        if data:
            detail = " ".join(
                part.decode("utf-8", errors="ignore")
                if isinstance(part, bytes)
                else str(part)
                for part in data
            )
        raise YahooImapError(
            "El servidor rechazó el acceso IMAP"
            + (f" ({detail.strip()})" if detail.strip() else "")
            + ". Usa una contraseña de aplicación nueva."
        )
    return client


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Comprueba usuario/contraseña de aplicación contra Yahoo IMAP."""
    verify_imap_login(address, app_password, brand="yahoo")


def verify_imap_login(
    address: str,
    app_password: str,
    *,
    brand: str = "yahoo",
    host: str | None = None,
) -> str:
    """Comprueba IMAP del proveedor y devuelve el host usado."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)
    brand = normalize_imap_brand(brand, address)
    profile = IMAP_BRANDS.get(brand)
    if not profile:
        raise YahooImapError("Ese proveedor de correo no está activo.")
    label = str(profile["label"])
    assert_address_allowed_for_brand(address, brand)
    if brand == "company":
        host = safe_imap_host(host)
    else:
        host = str(profile["host"] or "").strip()
        if not host:
            raise YahooImapError(f"No hay servidor IMAP para {label}.")

    if len(app_password) < 8:
        raise YahooImapError(
            f"La contraseña de aplicación de {label} es demasiado corta."
        )

    try:
        client = _open_yahoo_client(address, app_password, host=host)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise YahooImapError(
                    f"La contraseña es válida, pero no se pudo abrir el INBOX de {label}."
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
        return host
    except YahooImapError:
        raise
    except imaplib.IMAP4.error as error:
        err = str(error).lower()
        if "invalid" in err or "login" in err or "auth" in err:
            raise YahooImapError(
                f"{label} rechazó usuario o contraseña. "
                "Usa una contraseña de aplicación (no la del correo ni la de Donexto)."
            ) from error
        raise YahooImapError(
            f"{label} IMAP falló al autenticar: {error}"
        ) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise YahooImapError(
            f"No hubo respuesta de los servidores IMAP de {label} "
            f"({host}:993). Detalle de red: {error}"
        ) from error
    except Exception as error:
        raise YahooImapError(
            f"Error al conectar con {label} IMAP: {error}"
        ) from error


def list_yahoo_messages(
    address: str,
    app_password: str,
    *,
    max_results: int = 20,
    host: str | None = None,
) -> list[dict[str, Any]]:
    """Lista mensajes recientes del INBOX IMAP."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)
    max_results = max(1, min(int(max_results), 100))
    messages: list[dict[str, Any]] = []

    try:
        client = _open_yahoo_client(address, app_password, host=host)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise YahooImapError(
                    "No fue posible abrir el INBOX de Yahoo."
                )

            status, data = client.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

            ids = data[0].split()
            selected = list(reversed(ids[-max_results:]))

            for raw_id in selected:
                msg_id = raw_id.decode("ascii", errors="ignore")
                status, fetched = client.fetch(
                    raw_id,
                    "(FLAGS BODY.PEEK[HEADER])",
                )
                if status != "OK" or not fetched:
                    continue

                header_bytes = b""
                flags_text = ""
                for part in fetched:
                    if isinstance(part, tuple) and len(part) >= 2:
                        meta = part[0]
                        payload = part[1]
                        if isinstance(meta, bytes):
                            flags_text += meta.decode(
                                "utf-8", errors="ignore"
                            )
                        elif isinstance(meta, str):
                            flags_text += meta
                        if isinstance(payload, bytes) and payload:
                            header_bytes = payload

                parsed = email.message_from_bytes(header_bytes or b"")
                subject = _decode_header_value(parsed.get("Subject"))
                from_raw = _decode_header_value(parsed.get("From"))
                to_raw = _decode_header_value(parsed.get("To"))
                date_raw = parsed.get("Date")
                sender_name, sender_email = parseaddr(from_raw)
                received_at = None
                if date_raw:
                    try:
                        received_at = parsedate_to_datetime(
                            date_raw
                        ).isoformat()
                    except Exception:
                        received_at = date_raw

                is_unread = "\\Seen" not in flags_text
                snippet = re.sub(
                    r"\s+", " ", subject or "(sin vista previa)"
                ).strip()[:280]

                messages.append(
                    {
                        "id": msg_id,
                        "thread_id": msg_id,
                        "subject": subject or "(sin asunto)",
                        "sender": sender_name or from_raw or "Desconocido",
                        "sender_email": sender_email or None,
                        "recipient": to_raw or None,
                        "received_at": received_at,
                        "snippet": snippet,
                        "is_unread": is_unread,
                        "labels": ["YAHOO", "INBOX"],
                    }
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except YahooImapError:
        raise
    except Exception as error:
        raise YahooImapError(
            f"No fue posible leer correos de Yahoo: {error}"
        ) from error

    return messages


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
SENT_ALIASES = {"sent", "sent mail", "sent messages", "sent items", "enviados"}
DRAFT_ALIASES = {"draft", "drafts", "borradores"}
SPAM_ALIASES = {"bulk mail", "junk", "spam", "correo no deseado"}
TRASH_ALIASES = {"trash", "deleted", "deleted items", "papelera"}


def imap_search_date(value: datetime) -> str:
    current = value.astimezone(timezone.utc) if value.tzinfo else value.replace(
        tzinfo=timezone.utc
    )
    return f"{current.day:02d}-{IMAP_MONTHS[current.month - 1]}-{current.year}"


def classify_yahoo_folder(name: str) -> str:
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
