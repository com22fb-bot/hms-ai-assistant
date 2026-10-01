"""Llaves VAPID desde variable de entorno o, si falta, desde un archivo.

`npx web-push generate-vapid-keys` imprime la privada como base64url del
escalar P-256 (32 bytes). También se acepta PEM (PKCS#8 o SEC1), incluso
con saltos de línea escapados como \\n, que es lo habitual en Railway.
"""

from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def vapid_is_configured(
    *,
    public_key: str,
    private_material: str,
    private_path: str,
) -> bool:
    return bool(
        public_key.strip()
        and (private_material.strip() or private_path.strip())
    )


def public_key_for(private_key: ec.EllipticCurvePrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def raw_private_scalar(private_key: ec.EllipticCurvePrivateKey) -> str:
    scalar = private_key.private_numbers().private_value.to_bytes(32, "big")
    return base64.urlsafe_b64encode(scalar).rstrip(b"=").decode("ascii")


def parse_vapid_private_key(material: str) -> ec.EllipticCurvePrivateKey:
    text = _unwrap(material)
    if not text:
        raise ValueError("La llave privada VAPID está vacía.")
    if "BEGIN" in text:
        loaded = serialization.load_pem_private_key(text.encode("utf-8"), password=None)
    else:
        raw = _b64url_decode("".join(text.split()))
        if len(raw) == 32:
            loaded = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
        else:
            loaded = serialization.load_der_private_key(raw, password=None)
    return _require_p256(loaded)


def load_vapid_private_key(
    *,
    material: str | None = None,
    path: str | None = None,
) -> ec.EllipticCurvePrivateKey:
    """Prefiere el material en memoria. El archivo solo se usa si no hay material."""
    if (material or "").strip():
        return parse_vapid_private_key(material or "")
    file_path = (path or "").strip()
    if not file_path:
        raise ValueError(
            "Falta HMS_VAPID_PRIVATE_KEY o HMS_VAPID_PRIVATE_KEY_PATH."
        )
    return parse_vapid_private_key(Path(file_path).read_text(encoding="utf-8"))


def _require_p256(value: object) -> ec.EllipticCurvePrivateKey:
    if not isinstance(value, ec.EllipticCurvePrivateKey):
        raise ValueError("La llave VAPID no es una llave EC privada.")
    if not isinstance(value.curve, ec.SECP256R1):
        raise ValueError("La llave VAPID debe usar la curva P-256.")
    return value


def _unwrap(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return text.replace("\\n", "\n").strip()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except Exception as error:
        raise ValueError("La llave privada VAPID no es base64url ni PEM.") from error
