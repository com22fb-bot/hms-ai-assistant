"""L7reg1 (orden obligatorio de ASTRA, 14-oct-2026). Solo cerebro v1 (BRAIN_V1_ENABLED). Ejemplos propios, no del L7."""
import os

for k, v in {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "x",
             "OAUTH_ENCRYPTION_KEY": "test-oauth-encryption-key-32chars!!"}.items():
    os.environ.setdefault(k, v)

from app.services.brain_v1.analyzer import analyze, input_limit
from app.services.brain_v1.normalize import normalize
from app.services.brain_v1.phishing_v2 import detect
from app.services.brain_v1.protected import fold
from app.services.brain_v1.taxonomy_v2 import classify_v2

RX = "2026-10-13T10:00:00-06:00"


def _a(sender, subject, body):
    return analyze({"sender": sender, "subject": subject, "body_text": body, "received_at": RX, "labels": ["INBOX"],
                    "direction": "inbound"})


# 1) Triaje y fallback: sin área por defecto -------------------------------------------------------
def test_sender_words_never_decide_area():
    # "demo", "proyecto" o "equipo" en el remitente no convierten cualquier correo en Trabajo.
    r = _a("unknown@demo-proyecto.example", "Re: eso", "Confirmado. Gracias.")
    assert r.area is None
    r = _a("equipo@demo.example", "Tu factura", "Tu factura de luz por $480.00 vence el 20/11/2026.")
    assert r.area == "dinero"


def test_review_or_ambiguous_without_explicit_topic_is_por_revisar():
    for subject, body in (("Documento", "Aquí está lo que hablamos. Avísame."), ("Pago", "Quedó como comentamos.")):
        assert _a("ana@amigos.example", subject, body).area is None
    info = classify_v2("ambiguous", fold("hola\nquedo atento"), "x@y.example", 0.4, triage="review")
    assert info["area"] is None and info["review_reason"]


def test_review_with_explicit_topic_keeps_area_and_tie_goes_to_subject():
    info = classify_v2("ambiguous", fold("Póliza vigente\nTu póliza cubre internet y telefonía."), "x@y.example", 0.4,
                       triage="review")
    assert info["area"] == "salud"


def test_limit_inputs_go_to_review():
    assert input_limit("Hola", "") and input_limit("Hola", "   \n ")
    assert input_limit("Aviso", "Texto con ref\ufffdrencia rota")
    assert input_limit("Boletín", "palabra " * 2000)
    assert input_limit("Factura", "Tu factura de agua vence el 20/11/2026.") is None
    assert _a("system@x.example", "Aviso", "").area is None


# 2) Clasificación temática ---------------------------------------------------------------------
def test_personal_vs_business_invoice():
    assert _a("facturas@luz.example", "Recibo", "Tu recibo de luz por $612.00 vence el 25/11/2026.").area == "dinero"
    biz = _a("cobranza@nube.example", "Factura proveedor", "Factura por servicios de hosting. Total a pagar USD 300; vence el 30/11/2026.")
    assert biz.area == "trabajo"
    usd = _a("billing@app.example", "Your invoice", "Your invoice for $9.99 USD is due on 11/20/2026.")
    assert usd.area == "dinero"


def test_security_is_flag_not_area():
    r = _a("alertas@banco.example", "Nuevo inicio de sesión", "Detectamos un inicio de sesión desde un dispositivo nuevo. Si no fuiste tú, revisa.")
    assert r.area != "seguridad" and r.security_flag in {"N1", "N2"}


# 3) Seguridad, en orden ------------------------------------------------------------------------
def test_security_scenarios_detected():
    cases = {
        "pide_pin_o_contrasena": "Para evitar el bloqueo comparte tu PIN con este equipo.",
        "pago_falso": "Tu envío está retenido en almacén; paga $45 para liberarlo.",
        "fraude_ceo": "Soy el director general: transfiere hoy el pago a este proveedor nuevo.",
        "pide_datos_personales": "Felicidades, para reclamar el premio envía tus datos personales y tu identificación.",
        "cripto_deposito": "Deposita criptomonedas hoy y recibe el doble.",
    }
    for signal, body in cases.items():
        v = detect("x@desconocido.example", fold(body))
        accepted = {signal, "premio_pide_datos"} if signal == "pide_datos_personales" else {signal}
        assert v.is_phishing and accepted & set(v.signals), (signal, v.signals)


def test_ceo_secret_transfer_outside_process():
    assert detect("jefe@empresa.example", fold("Necesito una transferencia urgente y confidencial, fuera del proceso habitual.")).is_phishing
    v = detect("x@y.example", fold("Para la verificación solicita tu identificación y datos personales: es urgente."))
    assert "pide_datos_personales" in v.signals


def test_crypto_is_n1_and_por_revisar():
    r = _a("promo@inversion.example", "Duplica tus criptoactivos", "Deposita bitcoin hoy para liberar tu ganancia.")
    assert r.security_flag == "N1" and r.area is None


def test_typos_still_detected_via_normalization():
    r = _a("x@soporte.example", "C0mparte tu contr@seña", "Comparte tu c0ntrase5a para no perder la cuenta.")
    assert r.security_flag == "N1"


def test_security_warnings_are_not_false_alarms():
    for body in ("Nunca te pediremos tu PIN. No compartas tu contraseña con nadie.",
                 "Tu factura de agua por $300.00 vence el 20/11/2026. No compartas tu contraseña.",
                 "Tu pedido 123 fue enviado y llegará el jueves."):
        assert not detect("avisos@servicio.example", fold(body)).is_phishing, body


# 4) Normalización ------------------------------------------------------------------------------
def test_normalization_leet_unicode_spacing():
    assert normalize("F@ctura véncïda") == "factura vencida"
    assert normalize("Nómin@ dispónible") == "nomina disponible"
    assert normalize("Ｆａｃｔｕｒａ") == "factura"
    assert normalize("tu   pago") == "tu pago"
    assert normalize("escribe a ana@correo.com") == "escribe a ana@correo.com"  # una dirección no se altera


def test_original_text_is_not_modified():
    msg = {"sender": "a@b.example", "subject": "F@ctura véncïda", "body_text": "Tu facturra por $10 vence el 20/11/2026.",
           "received_at": RX, "labels": ["INBOX"], "direction": "inbound"}
    before = dict(msg)
    analyze(msg)
    assert msg == before


def test_multilingual_keywords():
    assert _a("n@x.example", "Aviso de pagamento", "Sua fatura vence em 10/12/2026. Valor: $125.50.").area == "dinero"
    assert _a("n@x.example", "Confirmation de réservation", "Votre réservation est confirmée pour le 02/02/2027.").area == "viajes"
    assert _a("n@x.example", "Facture", "Votre facture de 40 EUR est à payer avant le 03/12/2026.").area == "dinero"


# 5) Etiquetas ----------------------------------------------------------------------------------
def test_escuela_not_on_every_hogar_mail():
    r = _a("admin@condominio.example", "Mantenimiento de casa",
           "El plomero hará una visita técnica. Consulta con la familia o escuela por el canal habitual.")
    assert "Escuela" not in (r.area_tags or [])
    s = _a("avisos@colegio.example", "Aviso escolar", "La junta escolar se realizará el 20/11/2026.")
    assert "Escuela" in (s.area_tags or [])


def test_seguro_tag_only_when_policy_is_the_topic():
    r = _a("polizas@aseguradora.example", "Póliza vigente", "Tu póliza de gastos médicos está vigente.")
    assert any("eguro" in t for t in r.area_tags)


def test_spam_tag():
    r = _a("bulk@marketing.example", "Oferta milagrosa solo hoy", "Mensaje no solicitado: producto milagro, compra ya.")
    assert r.area == "promociones" and "Spam" in r.area_tags


# 6) Fechas -------------------------------------------------------------------------------------
def test_dates_separate_and_explicit():
    inv = _a("cobros@luz.example", "Recibo", "Tu recibo de luz por $500.00 vence el 22/11/2026.")
    assert inv.dates.due_at.startswith("2026-11-22") and inv.dates.event_at is None
    ev = _a("avisos@colegio.example", "Aviso escolar", "El festival se realizará el 27/01/2027.")
    assert ev.dates.event_at.startswith("2027-01-27") and ev.dates.due_at is None


def test_today_is_never_due_at():
    r = _a("cobros@x.example", "Pago", "Paga hoy tu saldo pendiente de $300.")
    assert r.dates.due_at is None or not r.dates.due_at.startswith(RX[:10])


def test_no_date_is_invented():
    r = _a("cobros@luz.example", "Recibo", "Tu recibo de luz por $500.00 está disponible.")
    assert r.dates.due_at is None and r.dates.event_at is None


# L7reg2 (decisiones ASTRA a-d) ------------------------------------------------------------------
def test_a_fraud_is_review_plus_alert_without_reliable_topic():
    r = _a("ceo@empresa-x.example", "Urgente", "Soy el director general: transfiere hoy el depósito a esta cuenta nueva, es confidencial.")
    assert r.security_flag == "N1" and r.area is None and r.area_review_reason


def test_a_fraud_keeps_area_only_with_reliable_topic_and_alert_never_hidden():
    info = classify_v2("phishing_suspect", fold("Tu pedido 551 y tu membresía\nTu paquete del pedido 551 de tu suscripción está retenido; "
                                                "paga $40 para liberarlo."),
                       "x@y.example", 0.4, phishing=True)
    assert info["area"] == "compras" and info["security_flag"] == "N1" and info["review_reason"]


def test_b_review_with_explicit_topic_keeps_area_and_review_mark():
    info = classify_v2("ambiguous", fold("Póliza vigente\nTu póliza cubre internet y telefonía."), "x@y.example", 0.4,
                       triage="review")
    assert info["area"] == "salud" and info["review_reason"]


def test_c_charges_by_context():
    personal = _a("billing@servicio.example", "Paqüte retenid0", "Tu facturra por $489.00 vence el 13/11/2026.")
    assert personal.area == "dinero"
    order = _a("billing@tienda.example", "Factura", "La factura de tu pedido 7781 por $489.00 vence el 13/11/2026.")
    assert order.area == "compras"
    work = _a("cxp@consultores.example", "Factura", "Factura por servicios de consultoría; total a pagar $40,000.00, vence el 10/12/2026.")
    assert work.area == "trabajo"


def test_d_spam_is_only_a_secondary_tag_and_promo_is_not_spam():
    spam = _a("bulk@marketing.example", "Oferta milagrosa", "Mensaje no solicitado: producto milagro.")
    assert spam.area == "promociones" and "Spam" in spam.area_tags
    promo = _a("ofertas@tienda.example", "Rebajas", "30% de descuento en toda la tienda este fin de semana.")
    assert promo.area == "promociones" and "Spam" not in promo.area_tags
    from app.services.brain_v1.taxonomy_v2 import AREAS
    assert "spam" not in AREAS and "Spam" not in AREAS.values()
