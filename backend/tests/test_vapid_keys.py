import os
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.services.vapid_keys import (
    load_vapid_private_key,
    parse_vapid_private_key,
    public_key_for,
    raw_private_scalar,
    vapid_is_configured,
)


def _fresh_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def _pem(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


class VapidKeyTests(unittest.TestCase):
    def test_web_push_base64url_scalar_roundtrips(self) -> None:
        key = _fresh_key()
        parsed = parse_vapid_private_key(raw_private_scalar(key))
        self.assertEqual(public_key_for(parsed), public_key_for(key))

    def test_pem_and_escaped_newlines(self) -> None:
        key = _fresh_key()
        pem = _pem(key)
        self.assertEqual(public_key_for(parse_vapid_private_key(pem)), public_key_for(key))
        escaped = '"' + pem.replace("\n", "\\n") + '"'
        self.assertEqual(
            public_key_for(parse_vapid_private_key(escaped)),
            public_key_for(key),
        )

    def test_material_wins_over_path(self) -> None:
        chosen = _fresh_key()
        other = _fresh_key()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(_pem(other))
            path = handle.name
        try:
            loaded = load_vapid_private_key(
                material=raw_private_scalar(chosen),
                path=path,
            )
            self.assertEqual(public_key_for(loaded), public_key_for(chosen))
        finally:
            os.unlink(path)

    def test_path_is_fallback_when_material_is_empty(self) -> None:
        key = _fresh_key()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(_pem(key))
            path = handle.name
        try:
            loaded = load_vapid_private_key(material="  ", path=path)
            self.assertEqual(public_key_for(loaded), public_key_for(key))
        finally:
            os.unlink(path)

    def test_missing_private_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            load_vapid_private_key(material="", path="")

    def test_configuration_accepts_env_key_without_a_file(self) -> None:
        self.assertTrue(
            vapid_is_configured(
                public_key="public",
                private_material="private",
                private_path="",
            )
        )
        self.assertFalse(
            vapid_is_configured(
                public_key="public",
                private_material="",
                private_path="",
            )
        )
        self.assertTrue(
            vapid_is_configured(
                public_key="public",
                private_material="",
                private_path="/tmp/vapid.pem",
            )
        )


if __name__ == "__main__":
    unittest.main()
