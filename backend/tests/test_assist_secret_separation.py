"""Separación de la firma de /asistencia respecto de OAUTH_ENCRYPTION_KEY (fixtures)."""
import os, time, unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import assist

OAUTH = "oauth-fixture-key-0000000000000000000000"
DED = "assist-fixture-secret-111111111111111111"


def env(**kw):
    base = {"OAUTH_ENCRYPTION_KEY": OAUTH, "ASSIST_TOKEN_SECRET": "", "ASSIST_LEGACY_VERIFY_UNTIL": ""}
    base.update(kw); return patch.dict(os.environ, base)


class AssistSeparation(unittest.TestCase):
    def test_sin_dedicada_comportamiento_historico(self):
        with env():
            t = assist.sign_token("session", "a@b.co", 60)
            self.assertEqual(assist.read_token(t, "session")["e"], "a@b.co")

    def test_con_dedicada_firma_nueva_independiente_de_oauth(self):
        with env(ASSIST_TOKEN_SECRET=DED):
            t = assist.sign_token("session", "a@b.co", 60)
        with env(ASSIST_TOKEN_SECRET=DED, OAUTH_ENCRYPTION_KEY="otra-oauth-key-99999999999999999999999"):
            self.assertEqual(assist.read_token(t, "session")["e"], "a@b.co")

    def test_token_viejo_aceptado_solo_en_ventana(self):
        with env():
            old = assist.sign_token("link", "a@b.co", 3600)
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL=str(time.time() + 3600)):
            self.assertEqual(assist.read_token(old, "link")["e"], "a@b.co")
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL="2020-01-01T00:00:00Z"):
            with self.assertRaises(assist.AssistTokenError):
                assist.read_token(old, "link")
        with env(ASSIST_TOKEN_SECRET=DED):
            with self.assertRaises(assist.AssistTokenError):
                assist.read_token(old, "link")
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL="basura"):
            with self.assertRaises(assist.AssistTokenError):
                assist.read_token(old, "link")

    def test_ventana_lejana_queda_cerrada(self):
        with env():
            old = assist.sign_token("link", "a@b.co", 3600)
        for far in (str(time.time() + 15 * 86400), "2099-01-01T00:00:00Z", "9999999999"):
            with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL=far):
                with self.assertRaises(assist.AssistTokenError):
                    assist.read_token(old, "link")

    def test_iso_sin_zona_es_utc(self):
        from datetime import datetime, timedelta, timezone
        with env():
            old = assist.sign_token("link", "a@b.co", 3600)
        naive = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(tzinfo=None).isoformat()
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL=naive):
            self.assertEqual(assist.read_token(old, "link")["e"], "a@b.co")

    def test_en_ventana_se_firma_con_dedicada(self):
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL=str(time.time() + 3600)):
            t = assist.sign_token("session", "a@b.co", 60)
        with env(ASSIST_TOKEN_SECRET=DED):
            self.assertEqual(assist.read_token(t, "session")["e"], "a@b.co")

    def test_codigo_emitido_con_llave_vieja_verifica_en_ventana(self):
        with env(), patch.object(assist, "allow_request", return_value=True):
            code, challenge = assist.new_code_challenge("a@b.co")
        with env(ASSIST_TOKEN_SECRET=DED, ASSIST_LEGACY_VERIFY_UNTIL=str(time.time() + 600)), \
                patch.object(assist, "allow_request", return_value=True):
            self.assertEqual(assist.verify_code(challenge, code)["status"], "verified")

    def test_dedicada_corta_cae_a_derivada(self):
        with env(ASSIST_TOKEN_SECRET="corta"):
            t = assist.sign_token("session", "a@b.co", 60)
        with env():
            self.assertEqual(assist.read_token(t, "session")["e"], "a@b.co")

    def test_sin_ninguna_llave_no_disponible(self):
        with env(OAUTH_ENCRYPTION_KEY=""):
            self.assertFalse(assist.assist_available())


if __name__ == "__main__": unittest.main()
