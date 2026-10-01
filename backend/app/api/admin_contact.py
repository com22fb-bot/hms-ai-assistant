"""Bandeja de contacto del panel /admin. Solo ADMIN_EMAILS."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.admin_ops import _require_admin
from app.services.contact_inbox import (
    archive_contact_message,
    authorize_contact_reply,
    create_contact_draft,
    list_contact_messages,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


class AuthorizeReplyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reply: str = Field(default="", max_length=8000)
    confirm: bool = False


@router.get("/contact-messages")
def admin_list_contact_messages(limit: int = 80) -> dict:
    _require_admin()
    return list_contact_messages(limit=limit)


@router.post("/contact-messages/{message_id}/draft")
def admin_draft_contact_message(message_id: str) -> dict:
    """Genera un borrador. No envía correo."""
    _require_admin()
    return create_contact_draft(message_id)


@router.post("/contact-messages/{message_id}/send")
def admin_send_contact_reply(
    message_id: str,
    payload: AuthorizeReplyRequest,
) -> dict:
    """Envía solo si el dueño manda confirm=true con el texto aprobado."""
    _require_admin()
    return authorize_contact_reply(
        message_id,
        payload.reply,
        confirm=payload.confirm,
    )


@router.post("/contact-messages/{message_id}/archive")
def admin_archive_contact_message(message_id: str) -> dict:
    _require_admin()
    return archive_contact_message(message_id)
