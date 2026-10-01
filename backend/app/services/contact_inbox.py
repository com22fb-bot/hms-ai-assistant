"""Bandeja de mensajes del formulario público.

El borrador de IA nunca se envía. El correo al visitante sale solo por
``authorize_contact_reply``, y ese camino usa la API HTTP de Resend.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.support_notify import (
    PUBLIC_CONTACT_INBOX,
    SMTPDeliveryError,
    contact_reply_subject,
    public_contact_subject,
    send_contact_reply_email,
)

logger = logging.getLogger(__name__)

STATUS_NUEVO = "nuevo"
STATUS_DRAFT = "borrador listo"
STATUS_REPLIED = "respondido"
STATUS_ARCHIVED = "archivado"
UNREAD_STATUSES = (STATUS_NUEVO, STATUS_DRAFT)
CONTACT_TABLE = "contact_messages"

UNCONFIGURED_MESSAGE = (
    "No hay un modelo de IA configurado (AI_PROVIDER=openai y OPENAI_API_KEY). "
    "Escribe la respuesta a mano y luego autoriza el envío."
)
DRAFT_FAILED_MESSAGE = (
    "No se pudo redactar con IA. Escribe la respuesta a mano y luego autoriza el envío."
)
INBOX_UNAVAILABLE_MESSAGE = (
    "La bandeja de mensajes no está lista. "
    "Aplica la migración contact_messages en Supabase."
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_IP_PEPPER = "donexto-contact-ip-v1"
_LANG_NAMES = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
}

DONEXTO_REPLY_FACTS = """
Donexto product facts (do not invent beyond these):
- Donexto reads only the user's authorized email, and only in read-only mode.
- It turns that mail into actionable life events.
- Microsoft Outlook and Hotmail are live today.
- Gmail, Yahoo, and iCloud are coming soon.
- Support address: support@donexto.com
- The app is at https://app.donexto.com
- The marketing site is https://www.donexto.com
""".strip()

_PUBLIC_FIELDS = (
    "id",
    "name",
    "email",
    "country",
    "message",
    "language",
    "subject",
    "status",
    "draft_body",
    "draft_error",
    "reply_body",
    "replied_at",
    "created_at",
    "updated_at",
)


def hash_contact_ip(ip: str) -> str:
    """One-way visitor address. Raw IPs are not stored."""
    salt = os.getenv("CONTACT_IP_HASH_SALT", "").strip() or _IP_PEPPER
    material = f"{salt}|{(ip or '').strip()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def ai_reply_configured() -> bool:
    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    if provider != "openai":
        return False
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def reply_language_instruction(language: str) -> str:
    code = (language or "").strip().lower()[:12]
    name = _LANG_NAMES.get(code[:2])
    if code[:2] == "es":
        return "Write the reply in Mexican Spanish."
    if name:
        return f"Write the reply in {name}."
    return "Write the reply in the same language as the visitor's message."


def build_reply_instructions(language: str) -> str:
    return "\n".join(
        [
            "You draft a support reply for Donexto.",
            "The owner reviews and edits this draft before anyone sends it.",
            "Never say the reply was already sent. Never include a subject line.",
            "Plain text only. No markdown. Be concise, warm, and accurate.",
            reply_language_instruction(language),
            "",
            DONEXTO_REPLY_FACTS,
        ]
    )


def build_reply_input(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Name: {row.get('name') or '(not given)'}",
            f"Email: {row.get('email') or ''}",
            f"Country: {row.get('country') or '(not given)'}",
            f"Language code: {row.get('language') or '(not given)'}",
            "Message:",
            str(row.get("message") or "").strip(),
        ]
    )


def generate_reply_text(row: dict[str, Any]) -> str:
    """Call the same OpenAI config used for mail summaries. Never sends mail."""
    if not ai_reply_configured():
        raise RuntimeError("ai_unconfigured")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("openai_missing") from error

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=build_reply_instructions(str(row.get("language") or "")),
        input=build_reply_input(row),
        store=False,
    )
    text = str(getattr(response, "output_text", "") or "").strip()
    if not text:
        raise RuntimeError("empty_draft")
    return text[:8000]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client() -> Any:
    from app.database.supabase import get_supabase_client

    return get_supabase_client()


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _inbox_error(error: Exception) -> HTTPException:
    logger.warning("Bandeja de contacto no disponible: %s", type(error).__name__)
    return HTTPException(
        status_code=503,
        detail={
            "status": "inbox_unavailable",
            "message": INBOX_UNAVAILABLE_MESSAGE,
        },
    )


def _require_id(message_id: str) -> str:
    clean = (message_id or "").strip()
    if not _UUID_RE.fullmatch(clean):
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "message": "Ese mensaje no está en la bandeja.",
            },
        )
    return clean


def public_contact_view(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in _PUBLIC_FIELDS}


def persist_public_contact(
    *,
    message_id: str,
    name: str,
    email: str,
    country: str,
    message: str,
    lang: str,
    ip: str,
) -> str | None:
    """Store a message that was already emailed to support. Never raises."""
    try:
        created = _now()
        payload = {
            "id": message_id,
            "name": name,
            "email": email,
            "country": country,
            "message": message,
            "language": lang,
            "subject": public_contact_subject(name),
            "status": STATUS_NUEVO,
            "ip_hash": hash_contact_ip(ip),
            "draft_body": None,
            "draft_error": None,
            "reply_body": None,
            "replied_at": None,
            "created_at": created,
            "updated_at": created,
        }
        _client().table(CONTACT_TABLE).insert(payload).execute()
        return message_id
    except Exception as error:  # noqa: BLE001 — el correo ya salió
        logger.warning(
            "No se guardó el mensaje de contacto: %s",
            type(error).__name__,
        )
        return None


def _count_status(client: Any, status: str) -> int:
    response = (
        client.table(CONTACT_TABLE)
        .select("id", count="exact")
        .eq("status", status)
        .limit(1)
        .execute()
    )
    count = getattr(response, "count", None)
    if count is None:
        return len(_rows(response))
    return int(count)


def list_contact_messages(limit: int = 80) -> dict[str, Any]:
    bounded = max(1, min(int(limit or 80), 200))
    try:
        client = _client()
        response = (
            client.table(CONTACT_TABLE)
            .select("*")
            .order("created_at", desc=True)
            .limit(bounded)
            .execute()
        )
        rows = [public_contact_view(row) for row in _rows(response)]
        nuevo = _count_status(client, STATUS_NUEVO)
        draft_ready = _count_status(client, STATUS_DRAFT)
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        raise _inbox_error(error) from error
    return {
        "messages": rows,
        "total": len(rows),
        "nuevo": nuevo,
        "unread": nuevo + draft_ready,
    }


def get_contact_message(message_id: str) -> dict[str, Any]:
    clean = _require_id(message_id)
    try:
        response = (
            _client()
            .table(CONTACT_TABLE)
            .select("*")
            .eq("id", clean)
            .limit(1)
            .execute()
        )
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        raise _inbox_error(error) from error
    rows = _rows(response)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "message": "Ese mensaje no está en la bandeja.",
            },
        )
    return rows[0]


def _update_message(message_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    payload = {**fields, "updated_at": _now()}
    try:
        (
            _client()
            .table(CONTACT_TABLE)
            .update(payload)
            .eq("id", message_id)
            .execute()
        )
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        raise _inbox_error(error) from error
    return get_contact_message(message_id)


def create_contact_draft(message_id: str) -> dict[str, Any]:
    """Propose a reply. This function does not send email."""
    row = get_contact_message(message_id)
    if not ai_reply_configured():
        return {
            "status": "unconfigured",
            "message": UNCONFIGURED_MESSAGE,
            "contact": public_contact_view(row),
        }
    try:
        text = generate_reply_text(row)
    except Exception as error:  # noqa: BLE001 — el dueño puede escribir a mano
        logger.warning(
            "Borrador de contacto falló: %s",
            type(error).__name__,
        )
        try:
            saved = _update_message(message_id, {"draft_error": DRAFT_FAILED_MESSAGE})
        except HTTPException:
            saved = row
        return {
            "status": "draft_failed",
            "message": DRAFT_FAILED_MESSAGE,
            "contact": public_contact_view(saved),
        }
    fields: dict[str, Any] = {
        "draft_body": text,
        "draft_error": None,
    }
    if row.get("status") in (STATUS_NUEVO, STATUS_DRAFT, None, ""):
        fields["status"] = STATUS_DRAFT
    saved = _update_message(message_id, fields)
    return {
        "status": "draft_ready",
        "message": "Borrador listo. Revísalo antes de autorizar el envío.",
        "contact": public_contact_view(saved),
    }


def _safe_autodraft(message_id: str) -> None:
    try:
        create_contact_draft(message_id)
    except Exception:  # noqa: BLE001
        logger.warning("Borrador automático falló", exc_info=True)


def schedule_contact_draft(message_id: str) -> None:
    """Draft in the background when a model is configured. Never sends."""
    if not message_id or not ai_reply_configured():
        return
    threading.Thread(
        target=_safe_autodraft,
        args=(message_id,),
        daemon=True,
        name="donexto-contact-draft",
    ).start()


def authorize_contact_reply(
    message_id: str,
    reply: str,
    *,
    confirm: bool,
) -> dict[str, Any]:
    """Send only when the owner explicitly confirms."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "confirm_required",
                "message": "Confirma el envío antes de autorizar la respuesta.",
            },
        )
    text = (reply or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "empty_reply",
                "message": "Escribe la respuesta antes de autorizar el envío.",
            },
        )
    if len(text) > 8000:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "reply_too_long",
                "message": "La respuesta es demasiado larga.",
            },
        )
    row = get_contact_message(message_id)
    visitor = str(row.get("email") or "").strip()
    if not visitor or "@" not in visitor:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_recipient",
                "message": "Ese mensaje no tiene un correo de respuesta.",
            },
        )
    subject = contact_reply_subject(str(row.get("subject") or ""))
    try:
        delivered = send_contact_reply_email(
            to_addr=visitor,
            subject=subject,
            body=text,
        )
    except SMTPDeliveryError:
        logger.warning("Respuesta de contacto no se pudo enviar")
        raise HTTPException(
            status_code=502,
            detail={
                "status": "delivery_failed",
                "message": "No se pudo enviar la respuesta.",
            },
        ) from None
    if not delivered:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "delivery_unconfigured",
                "message": "El envío con Resend no está configurado.",
            },
        )
    sent_message = f"Respuesta enviada a {visitor} desde {PUBLIC_CONTACT_INBOX}."
    try:
        saved = _update_message(
            message_id,
            {
                "status": STATUS_REPLIED,
                "reply_body": text,
                "draft_body": text,
                "draft_error": None,
                "replied_at": _now(),
            },
        )
    except HTTPException:
        logger.warning("Respuesta enviada pero la bandeja no se pudo marcar")
        fallback = dict(row)
        fallback["status"] = STATUS_REPLIED
        fallback["reply_body"] = text
        fallback["draft_body"] = text
        return {
            "status": "sent",
            "message": (
                f"{sent_message} No se pudo marcar como respondido. "
                "No la vuelvas a enviar."
            ),
            "contact": public_contact_view(fallback),
        }
    return {
        "status": "sent",
        "message": sent_message,
        "contact": public_contact_view(saved),
    }


def archive_contact_message(message_id: str) -> dict[str, Any]:
    get_contact_message(message_id)
    saved = _update_message(message_id, {"status": STATUS_ARCHIVED})
    return {
        "status": "archived",
        "contact": public_contact_view(saved),
    }
