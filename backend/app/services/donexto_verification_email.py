"""Localized Donexto verification links sent through the configured SMTP relay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

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


class VerificationEmailUserNotFound(Exception):
    """Raised when the requested email has no matching Supabase account."""


class VerificationEmailDeliveryError(RuntimeError):
    """The account exists, but Donexto could not hand the message to a relay."""


def _user_from_admin_response(response: Any) -> Any:
    """Extract the ``user`` object from either an SDK model or a plain dict."""
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    return user


def _candidate_email(candidate: Any) -> str:
    if candidate is None:
        return ""
    raw = candidate.get("email") if isinstance(candidate, dict) else getattr(
        candidate, "email", None
    )
    if not isinstance(raw, str):
        return ""
    return raw.strip().lower()


def _candidate_id(candidate: Any) -> str:
    if candidate is None:
        return ""
    raw = candidate.get("id") if isinstance(candidate, dict) else getattr(
        candidate, "id", None
    )
    if not isinstance(raw, str):
        return ""
    return raw.strip()


def _confirmed_at(candidate: Any) -> Any:
    if candidate is None:
        return None
    if isinstance(candidate, dict):
        return candidate.get("email_confirmed_at")
    return getattr(candidate, "email_confirmed_at", None)


def _listed_users(response: Any) -> list[Any]:
    users = getattr(response, "users", None)
    if users is None and isinstance(response, dict):
        users = response.get("users") or []
    if users is None and isinstance(response, list):
        users = response
    if not isinstance(users, list):
        return []
    return users


def _find_user_by_id(client: Any, user_id: str) -> Any | None:
    clean_id = user_id.strip()
    if not clean_id:
        return None
    response = client.auth.admin.get_user_by_id(clean_id)
    user = _user_from_admin_response(response)
    if _candidate_id(user) or _candidate_email(user):
        return user
    return None


def _find_user_by_email(client: Any, email: str) -> Any | None:
    """Return the existing Supabase user for this email, or None.

    Looks up by email API first, then pages through ``list_users``. The first
    page alone is not enough: a real account past that page must still match.
    Provider errors propagate so they are not reported as "not found".
    """
    target = email.strip().lower()
    if "@" not in target:
        return None

    getter = getattr(client.auth.admin, "get_user_by_email", None)
    if callable(getter):
        try:
            raw = getter(target)
            found = _user_from_admin_response(raw) or raw
        except Exception:
            found = None
        if _candidate_email(found) == target:
            return found

    list_users = client.auth.admin.list_users
    seen: set[str] = set()
    for page in range(1, 51):
        try:
            response = list_users(page=page, per_page=200)
        except TypeError:
            response = list_users()
            page_users = _listed_users(response)
            for candidate in page_users:
                if _candidate_email(candidate) == target:
                    return candidate
            return None
        page_users = _listed_users(response)
        fresh = False
        for candidate in page_users:
            identity = _candidate_id(candidate) or _candidate_email(candidate)
            if not identity or identity in seen:
                continue
            seen.add(identity)
            fresh = True
            if _candidate_email(candidate) == target:
                return candidate
        if not fresh or len(page_users) < 200:
            break
    return None


def _resolve_link_type(user: Any) -> str:
    """``signup`` confirms a new address. ``magiclink`` re-proves one already confirmed.

    OAuth session minting often sets ``email_confirmed_at`` before Donexto's
    own link is clicked. ``auth.resend(type=signup)`` then sends nothing.
    """
    if _confirmed_at(user):
        return "magiclink"
    return "signup"


def _properties(response: Any) -> dict[str, Any]:
    properties = getattr(response, "properties", None)
    if properties is None and isinstance(response, dict):
        properties = response.get("properties")
    if isinstance(properties, dict):
        return properties
    if properties is None:
        return {}
    dumped = getattr(properties, "model_dump", None)
    if callable(dumped):
        data = dumped()
        if isinstance(data, dict):
            return data
    payload: dict[str, Any] = {}
    for key in ("hashed_token", "action_link", "verification_type", "email_otp"):
        if hasattr(properties, key):
            payload[key] = getattr(properties, key)
    return payload


def verification_token_from_generate_response(response: Any) -> tuple[str, str]:
    """Return ``(token_hash, type)`` without using the Supabase action URL.

    The action URL consumes the token before the app can post it to
    ``confirm-donexto``. The app link must carry the still-unused hash.
    """
    props = _properties(response)
    token = str(props.get("hashed_token") or "").strip()
    link_type = str(props.get("verification_type") or "").strip()
    action = str(props.get("action_link") or getattr(response, "action_link", "") or "").strip()
    if action and not token:
        parsed = urlparse(action)
        query = parse_qs(parsed.query)
        token = (query.get("token") or query.get("token_hash") or [""])[0].strip()
        if not link_type:
            link_type = (query.get("type") or [""])[0].strip()
    if not token:
        raise ValueError("Supabase no devolvió el token de verificación")
    return token, link_type or "signup"


def app_verification_link(redirect_to: str, token_hash: str, token_type: str) -> str:
    parsed = urlparse(redirect_to)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["donexto_verify"] = "1"
    query["token_hash"] = token_hash
    query["type"] = token_type or "signup"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _generate_link(client: Any, *, email: str, link_type: str, redirect_to: str) -> Any:
    payload = {
        "type": link_type,
        "email": email,
        "options": {"redirect_to": redirect_to},
    }
    try:
        return client.auth.admin.generate_link(payload)
    except TypeError:
        return client.auth.admin.generate_link(
            {"type": link_type, "email": email}
        )


def send_verification_email(
    *,
    client: Any,
    email: str,
    language: object,
    redirect_to: str,
    user_id: str | None = None,
) -> VerificationEmail:
    """Send a localized verification email only for an already-existing account.

    Never calls ``generate_link`` for an email that does not exist in
    Supabase. This prevents the ``signup`` link type from silently creating
    new users during a resend flow. Raises ``VerificationEmailUserNotFound``
    so the caller can log it internally while still returning the same
    public response, preventing account enumeration.

    Delivery uses ``SUPPORT_SMTP_*`` (from ``support@donexto.com`` when that
    is ``SUPPORT_SMTP_FROM``) or ``RESEND_API_KEY``. It does not use
    ``auth.resend``, which ignores these templates and skips already
    confirmed OAuth accounts.
    """
    existing = None
    if isinstance(user_id, str) and user_id.strip():
        existing = _find_user_by_id(client, user_id)
        if existing is not None:
            found_email = _candidate_email(existing)
            if found_email and found_email != email.strip().lower():
                existing = None
    if existing is None:
        existing = _find_user_by_email(client, email)
    if existing is None:
        raise VerificationEmailUserNotFound(email)

    link_type = _resolve_link_type(existing)
    response = _generate_link(
        client,
        email=email,
        link_type=link_type,
        redirect_to=redirect_to,
    )
    token_hash, actual_type = verification_token_from_generate_response(response)
    message = build_verification_email(
        language,
        app_verification_link(redirect_to, token_hash, actual_type or link_type),
    )
    from app.services.support_notify import send_transactional_email

    delivered = send_transactional_email(email, message.subject, message.body)
    if not delivered:
        raise VerificationEmailDeliveryError(
            "No hay relay SMTP ni RESEND_API_KEY para el correo de Donexto"
        )
    return message
