"""Localized Donexto verification links sent through the configured SMTP relay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from app.services.support_notify import _send_via_smtp


@dataclass(frozen=True)
class VerificationEmail:
    subject: str
    body: str


_TEMPLATES: dict[str, tuple[str, str]] = {
    "es": (
        "Confirma tu correo de Donexto",
        (
            "Confirma tu correo de Donexto abriendo este enlace:\n\n"
            "{link}\n\n"
            "Este enlace protege tu cuenta Donexto. "
            "Si no lo solicitaste, puedes ignorar este correo."
        ),
    ),
    "en": (
        "Confirm your Donexto email",
        (
            "Confirm your Donexto email by opening this link:\n\n"
            "{link}\n\n"
            "This link keeps your Donexto account protected. "
            "If you did not request it, you can ignore this email."
        ),
    ),
    "fr": (
        "Confirmez votre e-mail Donexto",
        (
            "Confirmez votre e-mail Donexto en ouvrant ce lien :\n\n"
            "{link}\n\n"
            "Ce lien protège votre compte Donexto. "
            "Si vous ne l'avez pas demandé, ignorez cet e-mail."
        ),
    ),
    "it": (
        "Conferma la tua email Donexto",
        (
            "Conferma la tua email Donexto aprendo questo link:\n\n"
            "{link}\n\n"
            "Questo link protegge il tuo account Donexto. "
            "Se non lo hai richiesto, puoi ignorare questa email."
        ),
    ),
    "pt": (
        "Confirme o seu e-mail Donexto",
        (
            "Confirme o seu e-mail Donexto abrindo este link:\n\n"
            "{link}\n\n"
            "Este link protege a sua conta Donexto. "
            "Se você não solicitou, pode ignorar este e-mail."
        ),
    ),
}


def normalize_language(value: object) -> str:
    v = str(value or "").strip().lower()
    # Accept region tags like "es-ES" or "pt-BR" and reduce to base language.
    if "-" in v:
        v = v.split("-", 1)[0]
    if "_" in v:
        v = v.split("_", 1)[0]
    return v if v in _TEMPLATES else "es"


def build_verification_email(language: object, action_link: str) -> VerificationEmail:
    subject, body = _TEMPLATES[normalize_language(language)]
    return VerificationEmail(
        subject=subject,
        body=body.replace("{link}", action_link),
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


def _user_from_admin_response(response: Any) -> Any:
    """Extract the ``user`` object from either an SDK model or a plain dict."""
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    return user


def _find_user_by_email(client: Any, email: str) -> Any | None:
    """Return the existing Supabase user for this email, or None."""
    try:
        response = client.auth.admin.list_users()
        users = getattr(response, "users", None)
        if users is None and isinstance(response, dict):
            users = response.get("users") or []
        if users is None and isinstance(response, list):
            users = response
        target = email.strip().lower()
        for candidate in users or []:
            candidate_email = (
                getattr(candidate, "email", None)
                or (candidate.get("email") if isinstance(candidate, dict) else None)
                or ""
            )
            if str(candidate_email).strip().lower() == target:
                return candidate
    except Exception:
        return None
    return None


def _email_already_confirmed(client: Any, email: str) -> bool:
    """Best-effort check: does the given email already have a confirmed account?

    Falls back to ``False`` on any error so we always default to the ``signup``
    flow, which is safe for unconfirmed users (the 95% case).
    """
    user = _find_user_by_email(client, email)
    if user is None:
        return False
    confirmed_at = (
        getattr(user, "email_confirmed_at", None)
        or (user.get("email_confirmed_at") if isinstance(user, dict) else None)
    )
    return bool(confirmed_at)


def _resolve_link_type(client: Any, email: str) -> str:
    """Pick between ``signup`` (unconfirmed) and ``magiclink`` (re-verify).

    ``signup`` is the correct type for accounts that never confirmed their
    email: Supabase will mark ``email_confirmed_at`` on click. ``magiclink``
    is only used when the address already exists and is confirmed but we need
    to re-issue a Donexto verification link for some other reason.
    """
    if _email_already_confirmed(client, email):
        return "magiclink"
    return "signup"


def send_verification_email(
    *,
    client: Any,
    email: str,
    language: object,
    redirect_to: str,
) -> VerificationEmail:
    """Send a verification email only for an already-existing account.

    Never calls ``generate_link`` for an email that does not exist in
    Supabase. This prevents the ``signup`` link type from silently creating
    new users during a resend flow.
    """
    existing = _find_user_by_email(client, email)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "user_not_found",
                "message": "No existe una cuenta Donexto con ese correo.",
            },
        )

    link_type = _resolve_link_type(client, email)
    response = client.auth.admin.generate_link(
        {
            "type": link_type,
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
