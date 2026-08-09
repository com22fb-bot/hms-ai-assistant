from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request

from app.database.supabase import get_supabase_client


@dataclass(frozen=True)
class AuthenticatedUser:
    """Trusted identity returned by Supabase Auth."""

    id: str
    email: str
    full_name: str
    raw_user_metadata: dict[str, Any]


@dataclass(frozen=True)
class WorkspaceContext:
    """Authenticated user plus the workspace and mailbox they may access."""

    user: AuthenticatedUser
    workspace_id: str
    workspace_name: str
    membership_role: str
    google_account: dict[str, Any] | None


_current_context: ContextVar[WorkspaceContext | None] = ContextVar(
    "hms_workspace_context",
    default=None,
)


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def _user_value(user: Any, key: str, default: Any = None) -> Any:
    if isinstance(user, dict):
        return user.get(key, default)

    return getattr(user, key, default)


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "").strip()

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": "Falta la sesión de la cuenta HMS.",
            },
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": "La sesión HMS enviada no es válida.",
            },
        )

    return token.strip()


def authenticate_request(request: Request) -> AuthenticatedUser:
    """Validate the bearer token against Supabase Auth and return trusted data."""

    access_token = _extract_bearer_token(request)
    client = get_supabase_client()

    try:
        response = client.auth.get_user(access_token)
    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": (
                    "La sesión HMS expiró o no pudo validarse. "
                    "Vuelve a iniciar sesión."
                ),
            },
        ) from error

    user = getattr(response, "user", None)

    if user is None and isinstance(response, dict):
        user = response.get("user")

    user_id = str(_user_value(user, "id", "") or "").strip()
    email = str(_user_value(user, "email", "") or "").strip().lower()
    metadata = _user_value(user, "user_metadata", {}) or {}

    if not isinstance(metadata, dict):
        metadata = {}

    if not user_id or not email:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": "Supabase no devolvió una identidad HMS completa.",
            },
        )

    try:
        UUID(user_id)
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": "El identificador interno de la cuenta HMS no es válido.",
            },
        ) from error

    full_name = str(metadata.get("full_name") or "").strip()

    return AuthenticatedUser(
        id=user_id,
        email=email,
        full_name=full_name,
        raw_user_metadata=metadata,
    )


def _ensure_profile(user: AuthenticatedUser) -> dict[str, Any]:
    client = get_supabase_client()
    response = (
        client.table("profiles")
        .select("id,email,full_name,is_active")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )
    profile = _first_row(response)

    if profile:
        if profile.get("is_active") is False:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "forbidden",
                    "message": "La cuenta HMS está desactivada.",
                },
            )
        return profile

    payload = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name or None,
        "is_active": True,
        "metadata": {},
    }

    created = _first_row(
        client.table("profiles").insert(payload).execute()
    )

    if not created:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "identity_not_ready",
                "message": (
                    "No fue posible preparar el perfil HMS. "
                    "Aplica primero la migración de identidad."
                ),
            },
        )

    return created


def _ensure_personal_workspace(user: AuthenticatedUser) -> None:
    """Crea workspace personal si el perfil no tiene membresía activa.

    No exige que el buzón de Gmail coincida con el email de la cuenta Donexto:
    se puede conectar cualquier cuenta de Google al workspace.
    """
    if _active_memberships(user.id):
        return

    client = get_supabase_client()

    try:
        client.rpc(
            "hms_ensure_personal_workspace",
            {"target_profile_id": user.id},
        ).execute()
    except Exception:
        # Fallback si la función no está en Supabase o falla el RPC.
        slug = f"personal-{user.id.replace('-', '')}"
        display = (
            user.full_name
            or user.email.split("@")[0]
            or "Usuario"
        )
        workspace = _first_row(
            client.table("workspaces")
            .upsert(
                {
                    "name": f"{display} — Personal",
                    "slug": slug,
                    "status": "active",
                    "owner_profile_id": user.id,
                },
                on_conflict="slug",
            )
            .execute()
        )
        if not workspace:
            workspace = _first_row(
                client.table("workspaces")
                .select("id")
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
        if not workspace:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "workspace_required",
                    "message": (
                        "No fue posible crear el espacio de trabajo. "
                        "Revisa que las migraciones de identidad estén "
                        "aplicadas en Supabase."
                    ),
                },
            )

        client.table("workspace_members").upsert(
            {
                "workspace_id": workspace["id"],
                "profile_id": user.id,
                "role": "owner",
                "status": "active",
            },
            on_conflict="workspace_id,profile_id",
        ).execute()

    if not _active_memberships(user.id):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "workspace_required",
                "message": (
                    "La cuenta Donexto no tiene espacio de trabajo activo. "
                    "Intenta de nuevo o contacta soporte."
                ),
            },
        )


def _active_memberships(user_id: str) -> list[dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("workspace_members")
        .select("workspace_id,profile_id,role,status,joined_at,created_at")
        .eq("profile_id", user_id)
        .eq("status", "active")
        .order("joined_at", desc=False)
        .order("created_at", desc=False)
        .execute()
    )
    return _rows(response)


def resolve_workspace_context(
    request: Request,
    user: AuthenticatedUser,
) -> WorkspaceContext:
    """Resolve the tenant boundary for the authenticated HMS user."""

    _ensure_profile(user)
    _ensure_personal_workspace(user)
    memberships = _active_memberships(user.id)

    if not memberships:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "workspace_required",
                "message": (
                    "La cuenta Donexto todavía no tiene un espacio de trabajo."
                ),
            },
        )

    requested_workspace = request.headers.get(
        "x-hms-workspace-id",
        "",
    ).strip()

    membership: dict[str, Any] | None = None

    if requested_workspace:
        membership = next(
            (
                item
                for item in memberships
                if str(item.get("workspace_id")) == requested_workspace
            ),
            None,
        )

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "forbidden",
                    "message": (
                        "La cuenta HMS no pertenece al espacio de trabajo "
                        "solicitado."
                    ),
                },
            )
    else:
        membership = memberships[0]

    workspace_id = str(membership.get("workspace_id") or "").strip()

    if not workspace_id:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "workspace_required",
                "message": "La membresía HMS no contiene un workspace válido.",
            },
        )

    client = get_supabase_client()
    workspace = _first_row(
        client.table("workspaces")
        .select("id,name,status,owner_profile_id")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    )

    if not workspace or str(workspace.get("status") or "active") != "active":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "workspace_unavailable",
                "message": "El espacio de trabajo HMS no está activo.",
            },
        )

    google_account = _first_row(
        client.table("communication_accounts")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("provider", "google")
        .eq("status", "active")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    return WorkspaceContext(
        user=user,
        workspace_id=workspace_id,
        workspace_name=str(workspace.get("name") or "Espacio HMS"),
        membership_role=str(membership.get("role") or "viewer"),
        google_account=google_account,
    )


def set_request_context(context: WorkspaceContext) -> Token[WorkspaceContext | None]:
    return _current_context.set(context)


def reset_request_context(token: Token[WorkspaceContext | None]) -> None:
    _current_context.reset(token)


def get_request_context_or_none() -> WorkspaceContext | None:
    return _current_context.get()


def require_request_context() -> WorkspaceContext:
    context = get_request_context_or_none()

    if context is None:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthorized",
                "message": "La operación requiere una sesión HMS validada.",
            },
        )

    return context


def require_google_account() -> tuple[WorkspaceContext, dict[str, Any]]:
    context = require_request_context()

    if not context.google_account:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "mailbox_required",
                "connected": False,
                "message": (
                    "La cuenta HMS no tiene un buzón Google conectado "
                    "en este espacio de trabajo."
                ),
                "start_url": "/auth/google/start",
            },
        )

    return context, context.google_account
