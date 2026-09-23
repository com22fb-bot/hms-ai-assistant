"""Localized Donexto verification links sent through the configured SMTP relay."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class VerificationEmail:
    subject: str
    body: str
    html: str


@dataclass(frozen=True)
class _Template:
    subject: str
    lead: str
    button: str
    note: str


_TEMPLATES: dict[str, _Template] = {
    "es": _Template(
        subject="Confirma tu correo de Donexto",
        lead="Confirma tu correo de Donexto abriendo este enlace:",
        button="Verificar",
        note=(
            "Este enlace protege tu cuenta Donexto. "
            "Si no lo solicitaste, puedes ignorar este correo."
        ),
    ),
    "en": _Template(
        subject="Confirm your Donexto email",
        lead="Confirm your Donexto email by opening this link:",
        button="Verify",
        note=(
            "This link keeps your Donexto account protected. "
            "If you did not request it, you can ignore this email."
        ),
    ),
    "fr": _Template(
        subject="Confirmez votre e-mail Donexto",
        lead="Confirmez votre e-mail Donexto en ouvrant ce lien :",
        button="Vérifier",
        note=(
            "Ce lien protège votre compte Donexto. "
            "Si vous ne l'avez pas demandé, ignorez cet e-mail."
        ),
    ),
    "it": _Template(
        subject="Conferma la tua email Donexto",
        lead="Conferma la tua email Donexto aprendo questo link:",
        button="Verifica",
        note=(
            "Questo link protegge il tuo account Donexto. "
            "Se non lo hai richiesto, puoi ignorare questa email."
        ),
    ),
    "pt": _Template(
        subject="Confirme o seu e-mail Donexto",
        lead="Confirme o seu e-mail Donexto abrindo este link:",
        button="Verificar",
        note=(
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


def resolve_verification_language(requested: object) -> str:
    """Language for the verification email, from the login screen only.

    The value is whatever the client sent for the login UI. Account metadata
    and the browser Accept-Language header are not consulted: a Microsoft or
    Yahoo account can keep ``user_metadata.language`` as ``en`` after the
    login strip is already Spanish. Empty or unknown values fall back to
    Spanish, which is the login default.
    """
    requested_text = str(requested or "").strip()
    if not requested_text:
        return "es"
    return normalize_language(requested_text)


# Homepage banner on www.donexto.com (1024×434). Wide, warm, and already
# served over HTTPS, so mail clients can load it without a cid attachment.
VERIFICATION_EMAIL_HERO_URL = "https://www.donexto.com/brand-youtube.jpg"
_HERO_WIDTH = 600


def _plain_body(template: _Template, action_link: str) -> str:
    return f"{template.lead}\n\n{action_link}\n\n{template.note}"


def _html_body(template: _Template, action_link: str, language: str) -> str:
    """Email-client HTML: tables and inline CSS, same link as the text part."""
    safe_link = html.escape(action_link, quote=True)
    subject = html.escape(template.subject)
    lead = html.escape(template.lead)
    note = html.escape(template.note)
    button = html.escape(template.button)
    lang = html.escape(language)
    return (
        "<!DOCTYPE html>"
        f'<html lang="{lang}">'
        "<head>"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>{subject}</title>"
        "</head>"
        '<body style="margin:0;padding:0;background:#f4f1ea;">'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">'
        f"{subject}"
        "</div>"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="background:#f4f1ea;margin:0;padding:0;">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" width="600" style="max-width:600px;background:#ffffff;'
        'border:1px solid #e6e1d6;border-radius:16px;">'
        '<tr><td style="padding:0;line-height:0;font-size:0;">'
        f'<img src="{VERIFICATION_EMAIL_HERO_URL}" width="{_HERO_WIDTH}" '
        'alt="Donexto" border="0" '
        'style="display:block;width:100%;max-width:600px;height:auto;'
        'border:0;outline:none;text-decoration:none;">'
        "</td></tr>"
        '<tr><td style="padding:28px 32px 0;font-family:Arial,Helvetica,sans-serif;">'
        '<p style="margin:0;font-size:13px;letter-spacing:0.14em;'
        'text-transform:uppercase;color:#0b6e66;font-weight:bold;">Donexto</p>'
        '<h1 style="margin:12px 0 0;font-size:22px;line-height:1.35;'
        f'color:#102027;font-weight:700;">{subject}</h1>'
        "</td></tr>"
        '<tr><td style="padding:16px 32px 0;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:16px;line-height:1.5;color:#24343a;">{lead}</td></tr>'
        '<tr><td align="center" style="padding:28px 32px 8px;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        '<tr><td bgcolor="#0b6e66" style="border-radius:10px;">'
        f'<a href="{safe_link}" '
        'style="display:inline-block;padding:14px 32px;'
        "font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:bold;"
        f'color:#ffffff;text-decoration:none;">{button}</a>'
        "</td></tr></table>"
        "</td></tr>"
        '<tr><td style="padding:8px 32px 0;font-family:Arial,Helvetica,sans-serif;'
        'font-size:13px;line-height:1.5;color:#5c6b70;">'
        f"{note}"
        "</td></tr>"
        '<tr><td style="padding:16px 32px 28px;font-family:Arial,Helvetica,sans-serif;'
        'font-size:12px;line-height:1.5;color:#5c6b70;word-break:break-all;">'
        f'<a href="{safe_link}" style="color:#0b6e66;">{safe_link}</a>'
        "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def build_verification_email(language: object, action_link: str) -> VerificationEmail:
    code = normalize_language(language)
    template = _TEMPLATES[code]
    return VerificationEmail(
        subject=template.subject,
        body=_plain_body(template, action_link),
        html=_html_body(template, action_link, code),
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


# Microsoft/Yahoo/Google OAuth users are already provider-confirmed.
# ``signup`` confirmation does not apply: Supabase accepts the call and
# sends nothing. The delivery that worked (2026-09-17) was always magiclink.
DONEXTO_VERIFY_LINK_TYPE = "magiclink"


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
    return token, link_type or DONEXTO_VERIFY_LINK_TYPE


def app_verification_link(redirect_to: str, token_hash: str, token_type: str) -> str:
    parsed = urlparse(redirect_to)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["donexto_verify"] = "1"
    query["token_hash"] = token_hash
    query["type"] = token_type or DONEXTO_VERIFY_LINK_TYPE
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

    Never calls ``generate_link`` or ``sign_in_with_otp`` for an email that
    does not exist in Supabase, so a resend cannot create a user. Raises
    ``VerificationEmailUserNotFound`` so the caller can log it internally
    while still returning the same public response for a missing account.

    The link type is always ``magiclink``. OAuth accounts are already
    confirmed by the provider; ``auth.resend(type=signup)`` returns success
    and Supabase/Resend emit no mail. ``sign_in_with_otp`` would send
    Supabase's default template instead of the localized body. Delivery is
    the localized body through ``SUPPORT_SMTP_*`` (from
    ``support@donexto.com`` when that is ``SUPPORT_SMTP_FROM``) or
    ``RESEND_API_KEY``.
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

    # OAuth accounts are provider-confirmed, so auth.resend(type="signup")
    # returns success and sends nothing. auth.resend also cannot request
    # type "magiclink". generate_link(type="magiclink") mints an unused
    # token_hash; the localized body (SMTP or Resend) carries the app URL.
    # sign_in_with_otp is not used: it would send Supabase's template, not
    # this body, and must never run for a missing account.
    response = _generate_link(
        client,
        email=email,
        link_type=DONEXTO_VERIFY_LINK_TYPE,
        redirect_to=redirect_to,
    )
    token_hash, actual_type = verification_token_from_generate_response(response)
    message = build_verification_email(
        language,
        app_verification_link(
            redirect_to,
            token_hash,
            actual_type or DONEXTO_VERIFY_LINK_TYPE,
        ),
    )
    from app.services.support_notify import send_transactional_email

    delivered = send_transactional_email(
        email,
        message.subject,
        message.body,
        html=message.html,
    )
    if not delivered:
        raise VerificationEmailDeliveryError(
            "No hay relay SMTP ni RESEND_API_KEY para el correo de Donexto"
        )
    logger.info("donexto_verify_send type=magiclink result=ok")
    return message
