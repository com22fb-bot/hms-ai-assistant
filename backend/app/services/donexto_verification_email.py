"""Localized Donexto verification links sent through the configured SMTP relay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


def _user_from_admin_response(response: Any) -> Any:
    """Extract the ``user`` object from either an SDK model or a plain dict."""
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    return user


def _find_user_by_email(client: Any, email: str) -> Any | None:
    """Return the existing Supabase user for this email, or None.

    Provider errors (e.g. Supabase outage) propagate to the caller instead of
    being swallowed, so they are distinguishable from a genuine "not found".
    """
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
    return None


class VerificationEmailUserNotFound(Exception):
    """Raised when the requested email has no matching Supabase account."""


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
    new users during a resend flow. Raises ``VerificationEmailUserNotFound``
    so the caller can log it internally while still returning the same
    public response, preventing account enumeration.
    """
    existing = _find_user_by_email(client, email)
    if existing is None:
        raise VerificationEmailUserNotFound(email)

    client.auth.resend(
        {
            "type": "signup",
            "email": email,
            "options": {"email_redirect_to": redirect_to},
        }
    )
    subject, _ = _TEMPLATES[normalize_language(language)]
    return VerificationEmail(subject=subject, body="")
