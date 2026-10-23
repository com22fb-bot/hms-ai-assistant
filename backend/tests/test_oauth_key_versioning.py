"""Llavero versionado de OAUTH_ENCRYPTION_KEY y re-cifrado (solo fixtures, sin red ni BD real)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import oauth_storage as ost
from scripts import reencrypt_oauth_credentials as rc
from tests.fake_supabase import FakeSupabase

LEGACY = "legacy-fixture-key-000000000000000000"
K2 = "k2-fixture-key-11111111111111111111111"
K3 = "k3-fixture-key-22222222222222222222222"


def env(**kw):
    base = {"OAUTH_ENCRYPTION_KEY": LEGACY, "OAUTH_ENCRYPTION_KEYRING": "", "OAUTH_ENCRYPTION_ACTIVE_KEY_ID": ""}
    base.update(kw)
    return patch.dict(os.environ, base)


class KeyringTests(unittest.TestCase):
    def test_sin_llavero_identico_al_historico(self):
        with env():
            c = ost._encrypt("tok")
            self.assertTrue(c.startswith("gAAAA"))
            self.assertNotIn("$", c)
            self.assertEqual(ost._build_fernet().decrypt(c.encode()).decode(), "tok")
            self.assertEqual(ost.key_version_of(c), "legacy")

    def test_cifra_con_llave_activa_y_lee_legado(self):
        with env():
            old = ost._encrypt("viejo")
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            new = ost._encrypt("nuevo")
            self.assertTrue(new.startswith("k2$"))
            self.assertEqual(ost._decrypt(new), "nuevo")
            self.assertEqual(ost._decrypt(old), "viejo")

    def test_rollback_a_legado_sigue_leyendo_k2(self):
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            new = ost._encrypt("x")
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}"):
            self.assertEqual(ost._decrypt(new), "x")
            self.assertNotIn("$", ost._encrypt("y"))

    def test_llave_retirada_falla_controlado(self):
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            new = ost._encrypt("x")
        with env(OAUTH_ENCRYPTION_KEYRING=f"k3:{K3}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k3"):
            with self.assertRaises(ost.OAuthCredentialError):
                ost._decrypt(new)

    def test_llave_legado_cambiada_no_descifra(self):
        with env():
            old = ost._encrypt("x")
        with env(OAUTH_ENCRYPTION_KEY="otra-llave-distinta-3333333333333333333"):
            with self.assertRaises(ost.OAuthCredentialError):
                ost._decrypt(old)

    def test_config_invalida(self):
        for ring, active in [("k2:corta", "k2"), ("K-2:" + K2, ""), (f"k2:{K2},k2:{K3}", "k2"),
                             (f"legacy:{K2}", ""), (f"k2:{K2}", "k9")]:
            with env(OAUTH_ENCRYPTION_KEYRING=ring, OAUTH_ENCRYPTION_ACTIVE_KEY_ID=active):
                with self.assertRaises(ost.OAuthConfigurationError):
                    ost._encrypt("x")

    def test_reencrypt_idempotente(self):
        with env():
            old = ost._encrypt("x")
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            v1, ch1 = ost.reencrypt_value(old)
            v2, ch2 = ost.reencrypt_value(v1)
            self.assertTrue(ch1)
            self.assertFalse(ch2)
            self.assertEqual(v1, v2)
            self.assertEqual(ost.reencrypt_value(None), (None, False))


class ReencryptScriptTests(unittest.TestCase):
    def _db(self):
        with env():
            rows = [{"id": f"0000000{i}", "access_token": ost._encrypt(f"a{i}"),
                     "refresh_token": ost._encrypt(f"r{i}") if i % 2 else None} for i in range(1, 6)]
        rows.append({"id": "00000009", "access_token": "gAAAAAbasura", "refresh_token": None})
        return FakeSupabase({"oauth_credentials": rows})

    def test_dry_run_solo_cuenta_y_no_escribe(self):
        db = self._db()
        before = [dict(r) for r in db.tables["oauth_credentials"]]
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            out = rc.run(db, batch=2)
        self.assertEqual(out["conteos"], {"filas": 6, "por_recifrar": 5, "indescifrables": 1})
        self.assertEqual(db.tables["oauth_credentials"], before)
        self.assertNotIn("a1", repr(out))

    def test_apply_reanudable_e_idempotente(self):
        db = self._db()
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"):
            first = rc.run(db, apply=True, after="00000003", batch=2)
            self.assertEqual(first["conteos"].get("recifradas"), 2)
            full = rc.run(db, apply=True, batch=2)
            self.assertEqual(full["conteos"].get("recifradas"), 3)
            self.assertEqual(full["conteos"].get("ya_en_llave_activa"), 2)
            again = rc.run(db, apply=True, batch=2)
            self.assertEqual(again["conteos"], {"filas": 6, "ya_en_llave_activa": 5, "indescifrables": 1})
            r = {x["id"]: x for x in db.tables["oauth_credentials"]}
            self.assertEqual(ost._decrypt(r["00000001"]["refresh_token"]), "r1")
            self.assertIsNone(r["00000002"]["refresh_token"])
            self.assertEqual(r["00000009"]["access_token"], "gAAAAAbasura")

    def test_carrera_no_pisa_escritura_concurrente(self):
        db = self._db()
        real = db.table

        def table(name):
            q = real(name)
            orig_update = q.update

            def update(payload):
                # simula un save_credentials concurrente justo antes del UPDATE
                db.tables["oauth_credentials"][0]["access_token"] = "k2$concurrente"
                return orig_update(payload)
            q.update = update
            return q
        with env(OAUTH_ENCRYPTION_KEYRING=f"k2:{K2}", OAUTH_ENCRYPTION_ACTIVE_KEY_ID="k2"), \
                patch.object(db, "table", side_effect=table):
            out = rc.run(db, apply=True, batch=10)
        self.assertGreaterEqual(out["conteos"].get("carrera_reintentar", 0), 1)
        self.assertEqual(db.tables["oauth_credentials"][0]["access_token"], "k2$concurrente")


if __name__ == "__main__":
    unittest.main()
