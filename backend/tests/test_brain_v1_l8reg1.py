"""L8reg1 (decisión ASTRA, 14-oct-2026). Solo cerebro v1 (BRAIN_V1_ENABLED). Ejemplos propios, no copiados del L8."""
import os

for k, v in {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "x",
             "OAUTH_ENCRYPTION_KEY": "test-oauth-encryption-key-32chars!!"}.items():
    os.environ.setdefault(k, v)

from app.services.brain_v1.analyzer import analyze
from app.services.brain_v1.phishing_v2 import detect
from app.services.brain_v1.protected import fold

RX = "2026-10-13T10:00:00-06:00"


def _a(sender, subject, body):
    return analyze({"sender": sender, "subject": subject, "body_text": body, "received_at": RX, "labels": ["INBOX"],
                    "direction": "inbound"})


def _s(sender, subject, body):
    return _a(sender, subject, body).signals()


# 1) Citas escolares y médicas conservan su área
def test_school_meeting_is_hogar_with_escuela_tag():
    r = _a("avisos@primaria.example", "Junta de padres", "La reunión escolar será el 2026-11-20 a las 17:00.")
    assert r.area == "hogar" and "Escuela" in r.area_tags and r.dates.event_at.startswith("2026-11-20")


def test_medical_consultation_is_salud():
    r = _a("agenda@centro.example", "Tu consulta", "Tu consulta médica está programada para el 2026-11-09 a las 09:30.")
    assert r.area == "salud" and r.dates.event_at.startswith("2026-11-09")


def test_server_maintenance_is_not_hogar():
    assert _a("ops@nube.example", "Aviso", "Mantenimiento de servidores del proyecto el 2026-11-02.").area != "hogar"


# 2) Fraude N1: alerta + Por revisar, nunca Dinero
def test_prize_asking_id_and_address_is_n1():
    s = _s("premios@x.example", "Cobra tu premio", "Manda tu identificación y domicilio para cobrar el premio.")
    assert s["security_flag"] == "N1" and s["area"] is None


def test_crypto_deposit_with_amount_is_n1_not_dinero():
    s = _s("wallet@x.example", "Tu saldo", "Envía 0.10 BTC primero para desbloquear tu saldo.")
    assert s["security_flag"] == "N1" and s["area"] is None


def test_confidential_transfer_is_n1_not_dinero():
    s = _s("direccion@x.example", "Urgente", "Soy tu directora. Transfiere hoy y mantén esto en secreto.")
    assert s["security_flag"] == "N1" and s["area"] is None


def test_warning_not_to_share_data_is_not_fraud():
    assert not detect("banco@banco.example", fold("Nunca envíes tu identificación ni domicilio por correo.")).is_phishing


# 3) Etiquetas
def test_promo_and_social_tags():
    assert "Ofertas y rebajas" in _a("news@tienda.example", "Temporada", "Mira las ofertas de la tienda. Darte de baja aquí.").area_tags
    r = _a("noti@app.example", "Actividad", "Hay una nueva interacción en tu perfil social.")
    assert r.area == "promociones" and "Redes sociales" in r.area_tags


# 4) Marca de revisión: tema único y claro → sin marca
def test_clear_single_topic_has_no_review_mark():
    s = _s("x@aseg.example", "Tu póliza", "La póliza de gastos médicos está vigente. Revisa coberturas en el portal.")
    assert s["area"] == "salud" and not s["review_reason"] and not s["area_review_reason"]


def test_mixed_topics_keep_review():
    s = _s("ana@amigos.example", "Pago", "Quedó como comentamos.")
    assert s["area"] is None and s["area_review_reason"]


# 5) Fechas explícitas
def test_phrase_dates():
    assert _a("p@prov.example", "Factura de proveedor", "Factura por servicios, orden de compra 12. Pago pactado para el 2026-11-30.").dates.due_at.startswith("2026-11-30")
    assert _a("f@x.example", "Échéance", "Votre facture personnelle doit être réglée avant le 2026-11-17.").dates.due_at.startswith("2026-11-17")
    assert _a("j@x.example", "Informe", "Entrega el informe del proyecto antes del 2026-11-12.").dates.due_at.startswith("2026-11-12")
    assert _a("e@x.example", "Entrega", "El paquete está previsto para el 2026-11-04 entre 15:00 y 19:00.").dates.event_at.startswith("2026-11-04")


def test_phrase_without_date_invents_nothing():
    r = _a("e@x.example", "Entrega", "El paquete está previsto para la próxima semana.")
    assert r.dates.event_at is None and r.dates.due_at is None
    r = _a("j@x.example", "Informe", "Entrega el informe antes del cierre.")
    assert r.dates.due_at is None


def test_hr_document_request_is_not_fraud():
    s = _s("rh@empresa.example", "Expediente", "Por favor envía tu INE, comprobante de domicilio y CURP a más tardar el viernes.")
    assert s["security_flag"] is None
