"""Localized Donexto verification links sent through the configured SMTP relay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.support_notify import _send_via_smtp


@dataclass(frozen=True)
class VerificationEmail:
    subject: str
    body: str


def normalize_language(value: object) -> str:
    return "en" if str(value or "").strip().lower() == "en" else "es"


def build_verification_email(language: object, action_link: str) -> VerificationEmail:
    selected = normalize_language(language)
    if selected == "en":
        return VerificationEmail(
            subject="Confirm your Donexto email",
            body=(
                "Confirm your Donexto email by opening this link:\n\n"
                f"{action_link}\n\n"
                "This link keeps your Donexto account protected. "
                "If you did not request it, you can ignore this email."
            ),
        )
    return VerificationEmail(
        subject="Confirma tu correo de Donexto",
        body=(
            "Confirma tu correo de Donexto abriendo este enlace:\n\n"
            f"{action_link}\n\n"
            "Este enlace protege tu cuenta Donexto. "
            "Si no lo solicitaste, puedes ignorar este correo."
        ),
    )


def action_link_from_generate_response(response: Any) -> str:
    properties = getattr(response, "properties", None)
    if properties is None and isinstance(response, dict):
        properties = response.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    link = str(properties.get("action_link") or "").strip()
    if link:
        return link
    link = str(getattr(response, "action_link", "") or "").strip()
    if link:
        return link
    raise ValueError("Supabase no devolvió un enlace de verificación")


def send_verification_email(
    *,
    client: Any,
    email: str,
    language: object,
    redirect_to: str,
) -> VerificationEmail:
    response = client.auth.admin.generate_link(
        {
            "type": "magiclink",
            "email": email,
            "options": {"redirect_to": redirect_to},
        }
    )
    message = build_verification_email(
        language,
        action_link_from_generate_response(response),
    )
    if not _send_via_smtp(email, message.subject, message.body):
        raise RuntimeError("No hay un relay SMTP configurado para Donexto")
    return message
