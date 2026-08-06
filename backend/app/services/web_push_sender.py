from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAX_WEB_PUSH_PLAINTEXT = 3993
RECORD_SIZE = 4096


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _public_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )


def _hkdf_expand_one(prk: bytes, info: bytes, length: int) -> bytes:
    if length > hashlib.sha256().digest_size:
        raise ValueError("Esta expansión HKDF solo admite un bloque SHA-256.")
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:length]


def encrypt_web_push_payload(
    *,
    payload: bytes,
    user_public_key_b64: str,
    auth_secret_b64: str,
) -> bytes:
    """Codifica una carga Web Push RFC 8291 usando aes128gcm."""
    if len(payload) > MAX_WEB_PUSH_PLAINTEXT:
        raise ValueError(
            f"La notificación excede {MAX_WEB_PUSH_PLAINTEXT} bytes."
        )

    user_public_bytes = _b64url_decode(user_public_key_b64)
    auth_secret = _b64url_decode(auth_secret_b64)
    if len(user_public_bytes) != 65 or user_public_bytes[0] != 0x04:
        raise ValueError("La llave p256dh del dispositivo no es válida.")
    if len(auth_secret) < 16:
        raise ValueError("El secreto auth del dispositivo no es válido.")

    user_public = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(),
        user_public_bytes,
    )
    application_private = ec.generate_private_key(ec.SECP256R1())
    application_public_bytes = _public_bytes(application_private.public_key())
    ecdh_secret = application_private.exchange(ec.ECDH(), user_public)

    prk_key = hmac.new(auth_secret, ecdh_secret, hashlib.sha256).digest()
    key_info = (
        b"WebPush: info\x00"
        + user_public_bytes
        + application_public_bytes
    )
    input_key_material = _hkdf_expand_one(prk_key, key_info, 32)

    salt = os.urandom(16)
    prk = hmac.new(salt, input_key_material, hashlib.sha256).digest()
    content_key = _hkdf_expand_one(
        prk,
        b"Content-Encoding: aes128gcm\x00",
        16,
    )
    nonce = _hkdf_expand_one(
        prk,
        b"Content-Encoding: nonce\x00",
        12,
    )

    plaintext_record = payload + b"\x02"
    ciphertext = AESGCM(content_key).encrypt(
        nonce,
        plaintext_record,
        b"",
    )
    if len(ciphertext) >= RECORD_SIZE:
        raise ValueError("La notificación no cabe en un registro Web Push.")

    header = (
        salt
        + RECORD_SIZE.to_bytes(4, "big")
        + bytes([len(application_public_bytes)])
        + application_public_bytes
    )
    return header + ciphertext


def _load_vapid_private_key(
    private_key_path: str,
) -> ec.EllipticCurvePrivateKey:
    value = serialization.load_pem_private_key(
        Path(private_key_path).read_bytes(),
        password=None,
    )
    if not isinstance(value, ec.EllipticCurvePrivateKey):
        raise ValueError("La llave VAPID no es una llave EC privada.")
    if not isinstance(value.curve, ec.SECP256R1):
        raise ValueError("La llave VAPID debe usar la curva P-256.")
    return value


def send_web_push(
    *,
    endpoint: str,
    p256dh: str,
    auth_secret: str,
    payload: dict[str, Any],
    vapid_private_key_path: str,
    vapid_public_key: str,
    vapid_subject: str,
    ttl: int = 900,
    timeout: float = 12.0,
) -> httpx.Response:
    """Envía una notificación Web Push sin dependencias externas adicionales."""
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("El endpoint Push debe ser una URL HTTPS válida.")

    private_key = _load_vapid_private_key(vapid_private_key_path)
    expected_public = _b64url_encode(_public_bytes(private_key.public_key()))
    if expected_public != vapid_public_key:
        raise ValueError("Las llaves VAPID pública y privada no coinciden.")

    audience = f"{parsed.scheme}://{parsed.netloc}"
    token = jwt.encode(
        {
            "aud": audience,
            "exp": int(time.time()) + 12 * 60 * 60,
            "sub": vapid_subject,
        },
        private_key,
        algorithm="ES256",
        headers={"typ": "JWT"},
    )
    encoded_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    body = encrypt_web_push_payload(
        payload=encoded_payload,
        user_public_key_b64=p256dh,
        auth_secret_b64=auth_secret,
    )

    return httpx.post(
        endpoint,
        content=body,
        headers={
            "Authorization": f"vapid t={token}, k={vapid_public_key}",
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "TTL": str(max(int(ttl), 0)),
        },
        timeout=timeout,
        follow_redirects=False,
    )
