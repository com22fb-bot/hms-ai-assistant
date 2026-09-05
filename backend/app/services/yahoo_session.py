"""Entrada Yahoo: OAuth en el sitio de Yahoo.

Tener correo Yahoo no da acceso a Donexto. El login solo abre sesión si
el correo ya es usuario. El alta ocurre solo con intent=signup.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from app.database.supabase import get_supabase_client
from app.security.donexto_verified import verified_app_metadata_patch
from app.security.identity import bootstrap_workspace_for_user


logger = logging.getLogger(__name__)

YAHOO_SIGNUP_VIA = "yahoo_oauth"


class YahooSessionError(RuntimeError):
    """No se pudo abrir la sesión Donexto tras firmar en Yahoo."""


def _user_payload(user: Any) -> dict[str, Any]:
    if user is None:
        return {}
    if isinstance(user, dict):
        metadata = user.get("user_metadata") or {}
        return {
            "id": str(user.get("id") or "").strip(),
            "email": str(user.get("email") or "").strip().lower(),
            "user_metadata": metadata if isinstance(metadata, dict) else {},
        }
    metadata = getattr(user, "user_metadata", None) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "id": str(getattr(user, "id", "") or "").strip(),
        "email": str(getattr(user, "email", "") or "").strip().lower(),
        "user_metadata": metadata,
    }


def _unwrap_user(response: Any) -> dict[str, Any]:
    if response is None:
        return {}
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user") or response
    return _user_payload(user)


def _already_registered(error: BaseException) -> bool:
    text = str(error).lower()
    return any(
        token in text
        for token in (
            "already registered",
            "already been registered",
            "user already exists",
            "already exists",
            "duplicate",
        )
    )


def _find_user_in_profiles(client: Any, email: str) -> dict[str, Any]:
    try:
        response = (
            client.table("profiles")
            .select("id,email")
            .eq("email", email)
            .limit(1)
            .execute()
        )
    except Exception:
        return {}
    data = getattr(response, "data", None)
    row = data[0] if isinstance(data, list) and data else None
    if not isinstance(row, dict) or not row.get("id"):
        return {}
    try:
        got = client.auth.admin.get_user_by_id(str(row["id"]))
    except Exception:
        return {"id": str(row["id"]), "email": email, "user_metadata": {}}
    return _unwrap_user(got) or {
        "id": str(row["id"]),
        "email": email,
        "user_metadata": {},
    }


def _find_user_by_email(client: Any, email: str) -> dict[str, Any]:
    found = _find_user_in_profiles(client, email)
    if found.get("id"):
        return found

    getter = getattr(client.auth.admin, "get_user_by_email", None)
    if callable(getter):
        try:
            got = getter(email)
            payload = _unwrap_user(got)
            if payload.get("id"):
                return payload
        except Exception:
            logger.debug("get_user_by_email no localizó %s", email, exc_info=True)

    return {}


def auth_user_exists(email: str) -> bool:
    """True si ya hay usuario Auth con ese correo."""
    clean = (email or "").strip().lower()
    if "@" not in clean:
        return False
    client = get_supabase_client()
    return bool(_find_user_by_email(client, clean).get("id"))


def _link_properties(response: Any) -> dict[str, Any]:
    props = getattr(response, "properties", None)
    if props is None and isinstance(response, dict):
        props = response.get("properties") or response
    if props is None:
        return {}
    if isinstance(props, dict):
        return props
    dumped = getattr(props, "model_dump", None)
    if callable(dumped):
        data = dumped()
        return data if isinstance(data, dict) else {}
    payload: dict[str, Any] = {}
    for key in ("hashed_token", "email_otp", "action_link", "verification_type"):
        if hasattr(props, key):
            payload[key] = getattr(props, key)
    return payload


def _session_payload(response: Any) -> dict[str, str]:
    session = getattr(response, "session", None)
    if session is None and isinstance(response, dict):
        session = response.get("session") or response
    if session is None:
        return {}
    if isinstance(session, dict):
        access = str(session.get("access_token") or "").strip()
        refresh = str(session.get("refresh_token") or "").strip()
        expires = session.get("expires_in")
    else:
        access = str(getattr(session, "access_token", "") or "").strip()
        refresh = str(getattr(session, "refresh_token", "") or "").strip()
        expires = getattr(session, "expires_in", None)
    if not access or not refresh:
        return {}
    payload = {
        "access_token": access,
        "refresh_token": refresh,
    }
    if expires is not None:
        payload["expires_in"] = str(int(expires))
    return payload


def _verify_otp(client: Any, params: dict[str, str]) -> dict[str, str]:
    return _session_payload(client.auth.verify_otp(params))


def _mint_session_from_link(client: Any, email: str) -> dict[str, str]:
    try:
        link = client.auth.admin.generate_link(
            {
                "type": "magiclink",
                "email": email,
                "options": {"redirect_to": "https://app.donexto.com/"},
            }
        )
    except TypeError:
        link = client.auth.admin.generate_link(
            {
                "type": "magiclink",
                "email": email,
            }
        )

    from_link = _session_payload(link)
    if from_link:
        return from_link

    user = _unwrap_user(link)
    props = _link_properties(link)
    hashed = str(props.get("hashed_token") or "").strip()
    otp = str(props.get("email_otp") or "").strip()
    action = str(props.get("action_link") or "").strip()
    query_token = ""
    if action:
        parsed = urlparse(action)
        query = parse_qs(parsed.query)
        query_token = (query.get("token") or query.get("token_hash") or [""])[0]

    attempts: list[dict[str, str]] = []
    if hashed:
        attempts.append({"type": "email", "token_hash": hashed, "email": email})
        attempts.append({"type": "magiclink", "token_hash": hashed, "email": email})
    if otp:
        attempts.append({"type": "email", "token": otp, "email": email})
        attempts.append({"type": "magiclink", "token": otp, "email": email})
    if query_token:
        attempts.append({"type": "email", "token": query_token, "email": email})
        attempts.append({"type": "magiclink", "token": query_token, "email": email})

    last_error: BaseException | None = None
    for params in attempts:
        try:
            minted = _verify_otp(client, params)
            if minted:
                return minted
        except Exception as error:  # noqa: BLE001 — probar el siguiente formato
            last_error = error
            logger.debug("verify_otp %s falló: %s", params.get("type"), error)

    if user.get("id") and last_error:
        logger.warning("generate_link devolvió usuario pero no sesión: %s", last_error)
    raise YahooSessionError(
        "Yahoo autenticó, pero no se pudo abrir la sesión en Donexto."
    )


def _ensure_yahoo_auth_user(
    client: Any,
    email: str,
    *,
    allow_create: bool = True,
    signup_via: str = YAHOO_SIGNUP_VIA,
) -> tuple[str, str | None]:
    """Localiza el usuario Auth. Solo crea uno si allow_create (alta explícita).

    Firmar en Yahoo o Microsoft prueba el correo: donexto_verified queda True
    en app_metadata (solo service role), no en user_metadata editable.
    """

    user_metadata = {"signup_via": signup_via}
    app_metadata = verified_app_metadata_patch()
    existing = _find_user_by_email(client, email)
    created_password: str | None = None

    if existing.get("id"):
        user_id = existing["id"]
        previous = existing.get("user_metadata") or {}
        if not isinstance(previous, dict):
            previous = {}
        merged_user = {**previous, **user_metadata}
        try:
            client.auth.admin.update_user_by_id(
                user_id,
                {
                    "email_confirm": True,
                    "user_metadata": merged_user,
                    "app_metadata": app_metadata,
                },
            )
        except Exception:
            logger.warning("No se pudo marcar donexto_verified en %s", email, exc_info=True)
        return user_id, None

    if not allow_create:
        raise YahooSessionError("no_donexto_account")

    created_password = secrets.token_urlsafe(48)
    try:
        created = client.auth.admin.create_user(
            {
                "email": email,
                "email_confirm": True,
                "password": created_password,
                "user_metadata": user_metadata,
                "app_metadata": app_metadata,
            }
        )
        payload = _unwrap_user(created)
        if payload.get("id"):
            return payload["id"], created_password
    except Exception as error:
        if not _already_registered(error):
            raise YahooSessionError(
                "Yahoo autenticó, pero no se pudo preparar la sesión."
            ) from error
        created_password = None

    try:
        link = client.auth.admin.generate_link(
            {
                "type": "magiclink",
                "email": email,
            }
        )
    except Exception as error:
        raise YahooSessionError(
            "Yahoo autenticó, pero no se encontró la sesión existente."
        ) from error

    payload = _unwrap_user(link)
    user_id = payload.get("id") or ""
    if not user_id:
        raise YahooSessionError(
            "Yahoo autenticó, pero no se pudo identificar la sesión."
        )
    try:
        client.auth.admin.update_user_by_id(
            user_id,
            {
                "email_confirm": True,
                "user_metadata": {
                    **(payload.get("user_metadata") or {}),
                    **metadata,
                },
            },
        )
    except Exception:
        logger.warning("No se pudo actualizar metadata Yahoo de %s", email, exc_info=True)
    return user_id, created_password


def mint_yahoo_session(
    email: str,
    *,
    allow_create: bool = True,
    signup_via: str = YAHOO_SIGNUP_VIA,
) -> dict[str, str]:
    """Usuario Auth + tokens. La clave del buzón nunca es password de Supabase."""

    client = get_supabase_client()
    user_id, created_password = _ensure_yahoo_auth_user(
        client,
        email,
        allow_create=allow_create,
        signup_via=signup_via,
    )

    session: dict[str, str] = {}
    if created_password:
        try:
            session = _session_payload(
                client.auth.sign_in_with_password(
                    {"email": email, "password": created_password}
                )
            )
        except Exception:
            logger.debug("sign_in_with_password del alta Yahoo no sirvió", exc_info=True)

    if not session:
        session = _mint_session_from_link(client, email)

    user, workspace_id = bootstrap_workspace_for_user(user_id, email)
    session["user_id"] = user.id
    session["workspace_id"] = workspace_id
    session["email"] = email
    return session


def mint_yahoo_session_or_http(
    email: str,
    *,
    allow_create: bool = True,
    signup_via: str = YAHOO_SIGNUP_VIA,
    provider_label: str = "Yahoo",
) -> dict[str, str]:
    try:
        return mint_yahoo_session(
            email,
            allow_create=allow_create,
            signup_via=signup_via,
        )
    except HTTPException:
        raise
    except YahooSessionError as error:
        if str(error) == "no_donexto_account":
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "no_donexto_account",
                    "message": (
                        f"{provider_label} confirmó el correo, pero no hay "
                        f"cuenta Donexto. Tener {provider_label} no da acceso. "
                        "Crea la cuenta primero."
                    ),
                },
            ) from error
        raise HTTPException(
            status_code=503,
            detail={
                "status": "yahoo_session_failed",
                "message": str(error),
            },
        ) from error
    except Exception as error:
        logger.exception("Sesión %s falló para %s", provider_label, email)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "yahoo_session_failed",
                "message": (
                    f"{provider_label} autenticó, pero no se pudo abrir Donexto. "
                    "Inténtalo de nuevo o escribe a support@donexto.com."
                ),
            },
        ) from error
