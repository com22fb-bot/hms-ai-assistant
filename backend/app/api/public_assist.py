"""Asistencia personalizada pública: verificar correo y chatear.

Sin sesión de Supabase. La prueba es un token firmado: el enlace del acuse
automático o el código de 6 dígitos enviado al correo. Sin escrituras en la
base de datos.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.public_contact import client_ip
from app.security.rate_limit import allow_request
from app.services.assist import (
    AssistTokenError,
    AssistUnavailable,
    chat_reply,
    new_code_challenge,
    normalize_email,
    redeem_link,
    send_code_email,
    session_email,
    verify_code,
)
from app.services.support_notify import SMTPDeliveryError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/assist", tags=["Public assist"])


class StartRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=120)
    lang: str = Field(default="es", max_length=12)
    website: str = Field(default="", max_length=500)


class VerifyRequest(BaseModel):
    challenge: str = Field(min_length=10, max_length=2000)
    code: str = Field(min_length=4, max_length=20)


class RedeemRequest(BaseModel):
    token: str = Field(min_length=10, max_length=2000)


class ChatTurn(BaseModel):
    role: str = Field(max_length=16)
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    session: str = Field(min_length=10, max_length=2000)
    messages: list[ChatTurn] = Field(min_length=1, max_length=40)
    lang: str = Field(default="es", max_length=12)


def _error(status_code: int, status: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"status": status, "message": message})


def _unavailable() -> HTTPException:
    return _error(503, "assist_unavailable", "La asistencia no está disponible en este momento.")


def _limit(key: str, max_requests: int, window_seconds: int = 600) -> None:
    if not allow_request(key, max_requests=max_requests, window_seconds=window_seconds):
        raise _error(429, "rate_limited", "Demasiados intentos. Espera unos minutos.")


@router.post("/start")
def start_assist(payload: StartRequest, request: Request) -> dict[str, Any]:
    ip = client_ip(request)
    _limit(f"assist-start-ip:{ip}", 6)
    try:
        email = normalize_email(payload.email)
    except ValueError:
        raise _error(422, "invalid_email", "Escribe un correo válido.") from None
    _limit(f"assist-start-email:{email}", 3)
    try:
        code, challenge = new_code_challenge(email)
    except AssistUnavailable:
        raise _unavailable() from None
    if payload.website:
        # Honeypot: same shape, no mail.
        return {"status": "sent", "challenge": challenge}
    try:
        delivered = send_code_email(email, code, payload.lang)
    except SMTPDeliveryError:
        logger.warning("assist_code_delivery_failed")
        raise _error(502, "delivery_failed", "No pudimos enviar el código. Inténtalo otra vez.") from None
    if not delivered:
        raise _unavailable()
    return {"status": "sent", "challenge": challenge}


@router.post("/verify")
def verify_assist(payload: VerifyRequest, request: Request) -> dict[str, Any]:
    _limit(f"assist-verify-ip:{client_ip(request)}", 20)
    try:
        return verify_code(payload.challenge, payload.code)
    except AssistUnavailable:
        raise _unavailable() from None
    except AssistTokenError as error:
        reason = str(error)
        if reason == "too_many_attempts":
            raise _error(429, "too_many_attempts", "Demasiados intentos. Pide un código nuevo.") from None
        if reason == "expired":
            raise _error(410, "expired", "El código venció. Pide uno nuevo.") from None
        raise _error(400, "bad_code", "Ese código no coincide.") from None


@router.post("/redeem")
def redeem_assist(payload: RedeemRequest, request: Request) -> dict[str, Any]:
    _limit(f"assist-redeem-ip:{client_ip(request)}", 20)
    try:
        return redeem_link(payload.token)
    except AssistUnavailable:
        raise _unavailable() from None
    except AssistTokenError as error:
        if str(error) == "expired":
            raise _error(410, "expired", "El enlace venció. Verifica tu correo con un código.") from None
        raise _error(400, "bad_link", "El enlace no es válido. Verifica tu correo con un código.") from None


@router.post("/chat")
def chat_assist(payload: ChatRequest, request: Request) -> dict[str, Any]:
    _limit(f"assist-chat-ip:{client_ip(request)}", 60)
    try:
        email = session_email(payload.session)
    except AssistUnavailable:
        raise _unavailable() from None
    except AssistTokenError:
        raise _error(401, "session_expired", "Tu verificación venció. Verifica tu correo otra vez.") from None
    _limit(f"assist-chat-email:{email}", 30)
    try:
        return chat_reply(email, [turn.model_dump() for turn in payload.messages], payload.lang)
    except ValueError:
        raise _error(422, "bad_messages", "Escribe un mensaje.") from None
