"""Caché corta de identidad y contexto para no llamar a Supabase 5-7 veces por petición.

- El token se valida primero localmente (firma ES256/RS256 con el JWKS público
  de Supabase y fecha de expiración). Un token falso o vencido se rechaza sin
  red. Si el JWKS no está disponible, se sigue con la validación remota.
- El resultado de Supabase Auth (``get_user``) se guarda por huella del token
  hasta 60 s (nunca más allá de su ``exp``). Solo se guardan cuentas ya
  verificadas: una cuenta sin verificar se vuelve a consultar en cada petición,
  así al confirmar su correo entra de inmediato.
- El contexto de workspace (perfil, membresía, workspace) se guarda 60 s por
  usuario y workspace pedido. El buzón activo NO se guarda: se consulta siempre.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Any, Callable, TypeVar

import jwt

T = TypeVar("T")

TTL_SECONDS = float(os.getenv("HMS_AUTH_CACHE_TTL", "60") or 60)
_MAX_ENTRIES = 4096


class _TTLCache:
    def __init__(self) -> None:
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            if item[0] <= now:
                self._data.pop(key, None)
                return None
            return item[1]

    def set(self, key: Any, value: Any, ttl: float) -> None:
        if ttl <= 0:
            return
        with self._lock:
            if len(self._data) >= _MAX_ENTRIES:
                now = time.monotonic()
                for k in [k for k, v in self._data.items() if v[0] <= now]:
                    self._data.pop(k, None)
                if len(self._data) >= _MAX_ENTRIES:
                    self._data.clear()
            self._data[key] = (time.monotonic() + ttl, value)

    def drop_where(self, predicate: Callable[[Any], bool]) -> None:
        with self._lock:
            for k in [k for k in self._data if predicate(k)]:
                self._data.pop(k, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


user_cache = _TTLCache()
context_cache = _TTLCache()


def token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clear_all() -> None:
    user_cache.clear()
    context_cache.clear()


def forget_user(user_id: str) -> None:
    context_cache.drop_where(lambda key: isinstance(key, tuple) and key[0] == user_id)


# --- Validación local del JWT -------------------------------------------------

class LocalTokenInvalid(Exception):
    """El token no tiene firma válida o ya venció."""


_jwks_client: Any = None
_jwks_lock = threading.Lock()


def _jwks_url() -> str:
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/auth/v1/.well-known/jwks.json" if base else ""


def _get_jwks_client() -> Any:
    global _jwks_client
    if _jwks_client is None:
        url = _jwks_url()
        if not url:
            return None
        with _jwks_lock:
            if _jwks_client is None:
                _jwks_client = jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=5)
    return _jwks_client


def local_claims(token: str) -> dict[str, Any] | None:
    """Claims verificados localmente, o ``None`` si no se puede verificar aquí.

    Lanza ``LocalTokenInvalid`` si el token es claramente inválido.
    """
    if os.getenv("HMS_LOCAL_JWT", "1").strip() == "0":
        return None
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise LocalTokenInvalid(str(error)) from error
    alg = str(header.get("alg") or "")
    if alg not in {"ES256", "RS256"}:
        # HS256 (secreto compartido) u otro: lo valida Supabase Auth.
        return None
    client = _get_jwks_client()
    if client is None:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientError:
        # JWKS caído o kid desconocido: no decidimos aquí.
        return None
    except jwt.PyJWTError as error:
        raise LocalTokenInvalid(str(error)) from error
    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            options={"verify_aud": False, "require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as error:
        raise LocalTokenInvalid(str(error)) from error


def ttl_for_claims(claims: dict[str, Any] | None) -> float:
    ttl = TTL_SECONDS
    if claims and claims.get("exp"):
        try:
            ttl = min(ttl, float(claims["exp"]) - time.time())
        except (TypeError, ValueError):
            pass
    return ttl
