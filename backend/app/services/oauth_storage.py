"""
Persistencia segura de cuentas y credenciales OAuth.

HMS AI Assistant
Sprint 1

Este servicio centraliza:

- Estados temporales OAuth.
- Cuentas de comunicación.
- Credenciales cifradas.
- Recuperación de conexiones después de reiniciar FastAPI.
- Desconexión de cuentas.

Proveedores previstos:

- google
- microsoft
- whatsapp
- imap

WhatsApp Personal y WhatsApp Business comparten el proveedor
"whatsapp" y se diferencian mediante metadata.account_type.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken


SUPPORTED_PROVIDERS = {
    "google",
    "microsoft",
    "whatsapp",
    "imap",
    "yahoo",
}

ACTIVE_ACCOUNT_STATUSES = {
    "active",
}


class OAuthStorageError(RuntimeError):
    """Error general de persistencia OAuth."""


class OAuthConfigurationError(OAuthStorageError):
    """Configuración incompleta o inválida."""


class OAuthStateError(OAuthStorageError):
    """Estado OAuth inválido, expirado o inexistente."""


class OAuthCredentialError(OAuthStorageError):
    """Credenciales inexistentes, corruptas o imposibles de descifrar."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    else:
        raise OAuthStorageError(
            f"Formato de fecha no compatible: {type(value).__name__}"
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()

    aliases = {
        "gmail": "google",
        "google_workspace": "google",
        "outlook": "microsoft",
        "hotmail": "microsoft",
        "microsoft365": "microsoft",
        "office365": "microsoft",
        "whatsapp_business": "whatsapp",
        "whatsapp_personal": "whatsapp",
        "yahoo_mail": "yahoo",
        "ymail": "yahoo",
    }

    normalized = aliases.get(normalized, normalized)

    if normalized not in SUPPORTED_PROVIDERS:
        raise OAuthStorageError(
            f"Proveedor no compatible: {provider}. "
            f"Permitidos: {sorted(SUPPORTED_PROVIDERS)}"
        )

    return normalized


def _get_supabase_client() -> Any:
    """
    Obtiene el cliente definido en app.database.supabase.

    Admite estos nombres para conservar compatibilidad con la
    implementación actual del proyecto:

    - supabase
    - supabase_client
    - client
    - get_supabase_client()
    """

    module = importlib.import_module("app.database.supabase")

    getter = getattr(module, "get_supabase_client", None)
    if callable(getter):
        client = getter()
        if client is not None:
            return client

    for attribute_name in (
        "supabase",
        "supabase_client",
        "client",
    ):
        client = getattr(module, attribute_name, None)
        if client is not None:
            return client

    raise OAuthConfigurationError(
        "No se encontró el cliente Supabase en "
        "app.database.supabase. Debe exportarse como "
        "'supabase', 'supabase_client', 'client' o mediante "
        "'get_supabase_client()'."
    )


def _get_encryption_secret() -> str:
    secret = os.getenv("OAUTH_ENCRYPTION_KEY", "").strip()

    if not secret:
        raise OAuthConfigurationError(
            "Falta OAUTH_ENCRYPTION_KEY en las variables del servidor "
            "(Railway Variables). Genera un secreto de 32+ caracteres y "
            "haz Redeploy."
        )

    if len(secret) < 32:
        raise OAuthConfigurationError(
            "OAUTH_ENCRYPTION_KEY debe tener al menos 32 caracteres."
        )

    return secret


def _build_fernet() -> Fernet:
    """
    Deriva una clave Fernet estable a partir del secreto del backend.

    El secreto original nunca se guarda en Supabase.
    """

    secret = _get_encryption_secret().encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    fernet_key = base64.urlsafe_b64encode(digest)

    return Fernet(fernet_key)


def _encrypt(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    encrypted = _build_fernet().encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def _decrypt(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    try:
        decrypted = _build_fernet().decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        raise OAuthCredentialError(
            "No fue posible descifrar las credenciales. "
            "Verifica que OAUTH_ENCRYPTION_KEY no haya cambiado."
        ) from exc


def _state_hash(raw_state: str) -> str:
    return hashlib.sha256(raw_state.encode("utf-8")).hexdigest()


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if not data:
        return None

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


class OAuthStorage:
    """Servicio de persistencia multicanal."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or _get_supabase_client()

    # ========================================================
    # WORKSPACES
    # ========================================================

    def get_or_create_default_workspace(self) -> dict[str, Any]:
        """
        Obtiene o crea el workspace inicial.

        Durante el Sprint 1 usamos un workspace predeterminado.
        Posteriormente se asociará al usuario autenticado.
        """

        slug = os.getenv(
            "DEFAULT_WORKSPACE_SLUG",
            "hms-ai-assistant",
        ).strip()

        name = os.getenv(
            "DEFAULT_WORKSPACE_NAME",
            "Donexto",
        ).strip()

        existing_response = (
            self.client.table("workspaces")
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        existing = _first_row(existing_response)

        if existing:
            return existing

        created_response = (
            self.client.table("workspaces")
            .insert(
                {
                    "name": name,
                    "slug": slug,
                    "status": "active",
                }
            )
            .execute()
        )

        created = _first_row(created_response)

        if not created:
            # Protege contra una creación concurrente.
            retry_response = (
                self.client.table("workspaces")
                .select("*")
                .eq("slug", slug)
                .limit(1)
                .execute()
            )

            created = _first_row(retry_response)

        if not created:
            raise OAuthStorageError(
                "No fue posible obtener o crear el workspace predeterminado."
            )

        return created

    # ========================================================
    # ESTADOS OAUTH
    # ========================================================

    def create_oauth_state(
        self,
        provider: str,
        ttl_minutes: int = 10,
        profile_id: str | UUID | None = None,
        workspace_id: str | UUID | None = None,
        return_to: str | None = None,
        state_prefix: str | None = None,
    ) -> str:
        """
        Crea y persiste un estado OAuth.

        Retorna el valor original que debe enviarse al proveedor.
        En Supabase solo se almacena su hash SHA-256.
        `state_prefix` viaja en el token (p. ej. login/signup) porque
        return_to se sanitiza a solo el origen.
        """

        normalized_provider = _normalize_provider(provider)

        if ttl_minutes < 1 or ttl_minutes > 60:
            raise OAuthStateError(
                "La vigencia del estado OAuth debe estar entre 1 y 60 minutos."
            )

        self.delete_expired_oauth_states()

        raw_state = secrets.token_urlsafe(48)
        prefix = (state_prefix or "").strip().lower()
        if prefix:
            raw_state = f"{prefix}.{raw_state}"
        hashed_state = _state_hash(raw_state)
        expires_at = _utc_now() + timedelta(minutes=ttl_minutes)

        payload: dict[str, Any] = {
            "state": hashed_state,
            "provider": normalized_provider,
            "expires_at": _to_iso(expires_at),
        }

        if profile_id is not None:
            payload["profile_id"] = str(profile_id)

        if workspace_id is not None:
            payload["workspace_id"] = str(workspace_id)

        if return_to:
            payload["return_to"] = return_to.strip()[:2000]

        response = (
            self.client.table("oauth_states")
            .insert(payload)
            .execute()
        )

        if not getattr(response, "data", None):
            raise OAuthStateError(
                "Supabase no confirmó la creación del estado OAuth."
            )

        return raw_state

    def load_oauth_state(
        self,
        raw_state: str,
        provider: str,
    ) -> dict[str, Any]:
        """Lee el estado sin borrarlo. Así un callback duplicado no lo quema antes del token."""
        if not raw_state:
            raise OAuthStateError("El estado OAuth está vacío.")

        normalized_provider = _normalize_provider(provider)
        hashed_state = _state_hash(raw_state)

        response = (
            self.client.table("oauth_states")
            .select("*")
            .eq("state", hashed_state)
            .eq("provider", normalized_provider)
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if not row:
            raise OAuthStateError(
                "El estado OAuth no existe, ya fue utilizado o no corresponde "
                "al proveedor."
            )

        expires_at = _parse_datetime(row.get("expires_at"))
        if expires_at is None or expires_at <= _utc_now():
            self.delete_oauth_state(raw_state)
            raise OAuthStateError("El estado OAuth expiró.")
        return row

    def delete_oauth_state(self, raw_state: str) -> None:
        if not raw_state:
            return
        hashed_state = _state_hash(raw_state)
        (
            self.client.table("oauth_states")
            .delete()
            .eq("state", hashed_state)
            .execute()
        )

    def consume_oauth_state(
        self,
        raw_state: str,
        provider: str,
    ) -> dict[str, Any]:
        """
        Valida y elimina un estado OAuth.

        Un estado solo puede utilizarse una vez.
        """

        if not raw_state:
            raise OAuthStateError("El estado OAuth está vacío.")

        normalized_provider = _normalize_provider(provider)
        hashed_state = _state_hash(raw_state)

        response = (
            self.client.table("oauth_states")
            .select("*")
            .eq("state", hashed_state)
            .eq("provider", normalized_provider)
            .limit(1)
            .execute()
        )

        row = _first_row(response)

        if not row:
            raise OAuthStateError(
                "El estado OAuth no existe, ya fue utilizado o no corresponde "
                "al proveedor."
            )

        expires_at = _parse_datetime(row.get("expires_at"))

        # Se elimina aunque haya expirado para impedir reutilización.
        (
            self.client.table("oauth_states")
            .delete()
            .eq("state", hashed_state)
            .execute()
        )

        if expires_at is None or expires_at <= _utc_now():
            raise OAuthStateError("El estado OAuth expiró.")

        return row

    def delete_expired_oauth_states(self) -> int:
        now_iso = _to_iso(_utc_now())

        response = (
            self.client.table("oauth_states")
            .delete()
            .lt("expires_at", now_iso)
            .execute()
        )

        data = getattr(response, "data", None)
        return len(data) if isinstance(data, list) else 0

    # ========================================================
    # CUENTAS
    # ========================================================

    def upsert_communication_account(
        self,
        provider: str,
        provider_account_id: str,
        email: str | None = None,
        phone: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        workspace_id: str | UUID | None = None,
        connected_by_profile_id: str | UUID | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        normalized_provider = _normalize_provider(provider)

        provider_account_id = provider_account_id.strip()

        if not provider_account_id:
            raise OAuthStorageError(
                "provider_account_id es obligatorio."
            )

        if workspace_id is None:
            raise OAuthStorageError(
                "workspace_id es obligatorio para guardar una cuenta OAuth."
            )

        existing_response = (
            self.client.table("communication_accounts")
            .select("*")
            .eq("workspace_id", str(workspace_id))
            .eq("provider", normalized_provider)
            .eq("provider_account_id", provider_account_id)
            .limit(1)
            .execute()
        )

        existing = _first_row(existing_response)

        payload = {
            "workspace_id": str(workspace_id),
            "provider": normalized_provider,
            "provider_account_id": provider_account_id,
            "email": email,
            "phone": phone,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "status": status,
            "connected_by_profile_id": (
                str(connected_by_profile_id)
                if connected_by_profile_id is not None
                else None
            ),
        }

        if existing:
            update_response = (
                self.client.table("communication_accounts")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )

            updated = _first_row(update_response)

            if not updated:
                raise OAuthStorageError(
                    "Supabase no confirmó la actualización de la cuenta."
                )

            return updated

        create_response = (
            self.client.table("communication_accounts")
            .insert(payload)
            .execute()
        )

        created = _first_row(create_response)

        if not created:
            raise OAuthStorageError(
                "Supabase no confirmó la creación de la cuenta."
            )

        return created

    def get_account(
        self,
        account_id: str | UUID,
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("communication_accounts")
            .select("*")
            .eq("id", str(account_id))
            .limit(1)
            .execute()
        )

        return _first_row(response)

    def get_active_account(
        self,
        provider: str,
        email: str | None = None,
        phone: str | None = None,
        workspace_id: str | UUID | None = None,
    ) -> dict[str, Any] | None:
        normalized_provider = _normalize_provider(provider)

        if workspace_id is None:
            raise OAuthStorageError(
                "workspace_id es obligatorio para buscar una cuenta activa."
            )

        query = (
            self.client.table("communication_accounts")
            .select("*")
            .eq("provider", normalized_provider)
            .eq("status", "active")
        )

        if workspace_id is not None:
            query = query.eq("workspace_id", str(workspace_id))

        if email:
            query = query.eq("email", email)

        if phone:
            query = query.eq("phone", phone)

        response = (
            query.order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        return _first_row(response)

    def list_accounts(
        self,
        provider: str | None = None,
        include_disconnected: bool = False,
        workspace_id: str | UUID | None = None,
    ) -> list[dict[str, Any]]:
        query = self.client.table("communication_accounts").select("*")

        if provider:
            query = query.eq(
                "provider",
                _normalize_provider(provider),
            )

        if workspace_id is not None:
            query = query.eq("workspace_id", str(workspace_id))

        if not include_disconnected:
            query = query.eq("status", "active")

        response = (
            query.order("created_at", desc=False)
            .execute()
        )

        data = getattr(response, "data", None)

        return data if isinstance(data, list) else []

    # ========================================================
    # CREDENCIALES
    # ========================================================

    def save_credentials(
        self,
        account_id: str | UUID,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | str | None = None,
        token_uri: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Guarda credenciales cifradas.

        Nunca se envían tokens en texto legible a Supabase.
        """

        account = self.get_account(account_id)

        if not account:
            raise OAuthCredentialError(
                f"No existe la cuenta {account_id}."
            )

        if not access_token:
            raise OAuthCredentialError(
                "El access token es obligatorio."
            )

        parsed_expiration = (
            _parse_datetime(expires_at)
            if expires_at is not None
            else None
        )

        existing_response = (
            self.client.table("oauth_credentials")
            .select("*")
            .eq("account_id", str(account_id))
            .limit(1)
            .execute()
        )

        existing = _first_row(existing_response)

        # Algunos proveedores no devuelven refresh_token en cada renovación.
        # Si no llega uno nuevo, se conserva el ya almacenado.
        encrypted_refresh_token: str | None

        if refresh_token:
            encrypted_refresh_token = _encrypt(refresh_token)
        elif existing:
            encrypted_refresh_token = existing.get("refresh_token")
        else:
            encrypted_refresh_token = None

        payload = {
            "account_id": str(account_id),
            "access_token": _encrypt(access_token),
            "refresh_token": encrypted_refresh_token,
            "expires_at": _to_iso(parsed_expiration),
            "token_uri": token_uri,
            "scopes": list(scopes or []),
            "metadata": metadata or {},
        }

        if existing:
            response = (
                self.client.table("oauth_credentials")
                .update(payload)
                .eq("account_id", str(account_id))
                .execute()
            )
        else:
            response = (
                self.client.table("oauth_credentials")
                .insert(payload)
                .execute()
            )

        saved = _first_row(response)

        if not saved:
            raise OAuthCredentialError(
                "Supabase no confirmó el guardado de las credenciales."
            )

        # No devolvemos los valores cifrados.
        return {
            "id": saved.get("id"),
            "account_id": saved.get("account_id"),
            "expires_at": saved.get("expires_at"),
            "token_uri": saved.get("token_uri"),
            "scopes": saved.get("scopes") or [],
            "metadata": saved.get("metadata") or {},
            "has_access_token": bool(saved.get("access_token")),
            "has_refresh_token": bool(saved.get("refresh_token")),
            "created_at": saved.get("created_at"),
            "updated_at": saved.get("updated_at"),
        }

    def get_credentials(
        self,
        account_id: str | UUID,
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("oauth_credentials")
            .select("*")
            .eq("account_id", str(account_id))
            .limit(1)
            .execute()
        )

        row = _first_row(response)

        if not row:
            return None

        return {
            "id": row.get("id"),
            "account_id": row.get("account_id"),
            "access_token": _decrypt(row.get("access_token")),
            "refresh_token": _decrypt(row.get("refresh_token")),
            "expires_at": _parse_datetime(row.get("expires_at")),
            "token_uri": row.get("token_uri"),
            "scopes": row.get("scopes") or [],
            "metadata": row.get("metadata") or {},
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def get_active_credentials(
        self,
        provider: str,
        email: str | None = None,
        phone: str | None = None,
        workspace_id: str | UUID | None = None,
    ) -> dict[str, Any] | None:
        account = self.get_active_account(
            provider=provider,
            email=email,
            phone=phone,
            workspace_id=workspace_id,
        )

        if not account:
            return None

        credentials = self.get_credentials(account["id"])

        if not credentials:
            return None

        return {
            "account": account,
            "credentials": credentials,
        }

    def credentials_are_expired(
        self,
        credentials: dict[str, Any],
        safety_seconds: int = 60,
    ) -> bool:
        expires_at = credentials.get("expires_at")

        if expires_at is None:
            return False

        parsed_expiration = _parse_datetime(expires_at)

        if parsed_expiration is None:
            return False

        return parsed_expiration <= (
            _utc_now() + timedelta(seconds=safety_seconds)
        )

    # ========================================================
    # DESCONEXIÓN
    # ========================================================

    def disconnect_account(
        self,
        account_id: str | UUID,
        delete_credentials: bool = True,
    ) -> bool:
        account = self.get_account(account_id)

        if not account:
            return False

        if delete_credentials:
            (
                self.client.table("oauth_credentials")
                .delete()
                .eq("account_id", str(account_id))
                .execute()
            )

        response = (
            self.client.table("communication_accounts")
            .update({"status": "disconnected"})
            .eq("id", str(account_id))
            .execute()
        )

        return bool(getattr(response, "data", None))


oauth_storage = OAuthStorage()
