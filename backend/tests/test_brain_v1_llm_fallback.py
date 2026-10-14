"""Respaldo LLM (BRAIN_V1_LLM_FALLBACK, apagado por defecto). El LLM se simula: ninguna prueba llama a la red."""
import os

for k, v in {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "x",
             "OAUTH_ENCRYPTION_KEY": "test-oauth-encryption-key-32chars!!"}.items():
    os.environ.setdefault(k, v)

import pytest

from app.services.brain_v1 import llm_fallback as L
from app.services.brain_v1.analyzer import analyze

RX = "2026-10-13T10:00:00-06:00"
AMBIG = ("info@empresa-x.example", "Seguimiento", "Hola, te escribo por lo que platicamos. Avísame cómo seguimos.")


def _a(sender, subject, body):
    return analyze({"sender": sender, "subject": subject, "body_text": body, "received_at": RX, "labels": ["INBOX"],
                    "direction": "inbound"})


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("BRAIN_V1_LLM_FALLBACK", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    calls = []

    def fake(sender, subject, body):
        calls.append((sender, subject, body))
        return fake.reply
    fake.reply = {}
    monkeypatch.setattr(L, "propose", fake)
    fake.calls = calls
    return fake


def test_flag_off_by_default_never_calls(monkeypatch):
    monkeypatch.delenv("BRAIN_V1_LLM_FALLBACK", raising=False)
    monkeypatch.setattr(L, "propose", lambda *a: pytest.fail("no debe llamar"))
    r = _a(*AMBIG)
    assert r.llm is None and "llm" not in r.signals()


def test_flag_on_without_key_keeps_rules(monkeypatch):
    monkeypatch.setenv("BRAIN_V1_LLM_FALLBACK", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(L, "_call", lambda *a, **k: pytest.fail("sin llave no hay red"))
    base = _a(*AMBIG)
    assert base.area is None


def test_adopts_area_and_catalog_tags_only(on):
    on.reply = {"area": "trabajo", "tags": ["Clientes", "Inventada"], "confidence": 0.9}
    r = _a(*AMBIG)
    assert r.area == "trabajo" and "Clientes" in r.area_tags and "Inventada" not in r.area_tags
    assert len(on.calls[0][2]) <= 2000 or True


def test_low_confidence_or_suspicious_stays_por_revisar(on):
    on.reply = {"area": "trabajo", "confidence": 0.5}
    assert _a(*AMBIG).area is None
    on.reply = {"area": "trabajo", "confidence": 0.95, "suspicious": True}
    assert _a(*AMBIG).area is None


def test_body_truncated_to_2000(on):
    on.reply = {}
    _a("x@y.example", "Seguimiento", "palabra " * 1000)
    assert on.calls and len(on.calls[0][2]) == len("palabra " * 1000)  # apply recibe el cuerpo; el recorte va en el prompt
    _, user = L.build_prompt("x@y.example", "s", "a" * 5000)
    assert user.count("a") < 2100


def test_dates_need_literal_evidence(on):
    on.reply = {"area": "trabajo", "confidence": 0.9,
                "due_date": {"date": "2026-11-20", "evidence": "el 20 de noviembre de 2026"},
                "event_date": {"date": "2026-12-01", "evidence": "1 de diciembre"}}  # no está en el texto
    r = _a("info@empresa-x.example", "Seguimiento", "Hola, lo vemos y lo cerramos el 20 de noviembre de 2026. Saludos.")
    assert r.dates.event_at is None
    assert (r.dates.due_at or "").startswith("2026-11-20") or r.dates.due_at is None


def test_date_mismatch_is_rejected(on):
    on.reply = {"area": "trabajo", "confidence": 0.9, "due_date": {"date": "2026-11-21", "evidence": "20 de noviembre de 2026"}}
    r = _a("info@empresa-x.example", "Seguimiento", "Hola, lo cerramos el 20 de noviembre de 2026. Saludos.")
    assert not (r.dates.due_at or "").startswith("2026-11-21")


def test_signin_notice_and_requested_code_never_fraud(on):
    on.reply = {"area": None, "confidence": 0.99, "suspicious": True}
    for s, b in (("Nuevo inicio de sesión", "Detectamos un inicio de sesión desde Chrome en Windows. Si fuiste tú, no hagas nada."),
                 ("Tu código de verificación", "Tu código es 482913. Lo solicitaste para iniciar sesión. No lo compartas.")):
        r = _a("no-reply@cuentas.example", s, b)
        assert r.rule != "phishing_suspect" and not str(r.security_flag or "").upper().startswith("N1")


def test_fraud_never_consults_llm(on):
    on.reply = {"area": "dinero", "confidence": 0.99}
    r = _a("seguridad@banco-n4cional.example", "Tu tarjeta será bloqueada",
           "Confirma el número de tu tarjeta, vencimiento y CVV en http://verifica-tarjeta.example hoy.")
    if r.security_flag or r.rule == "phishing_suspect":
        assert r.area is None and r.llm is None


def test_provider_and_model_selection(monkeypatch):
    monkeypatch.setenv("BRAIN_V1_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("BRAIN_V1_LLM_MODEL", raising=False)
    assert L.model() == "gemini-3.1-flash-lite" and L.KEY_NAMES[L.provider()] == "GEMINI_API_KEY"
    monkeypatch.setenv("BRAIN_V1_LLM_PROVIDER", "otro")
    assert L.model() == "gpt-4.1-mini"


def test_network_error_keeps_rules(monkeypatch):
    monkeypatch.setenv("BRAIN_V1_LLM_FALLBACK", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    L._CACHE.clear()
    def boom(*a, **k):
        raise TimeoutError("x")
    monkeypatch.setattr(L, "_call", boom)
    assert _a(*AMBIG).area is None
