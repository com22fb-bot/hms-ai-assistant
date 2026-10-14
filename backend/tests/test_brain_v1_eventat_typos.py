"""Fix event_at + seguridad robusta a faltas/homoglifos (cerebro v1, detrás de BRAIN_V1_ENABLED)."""
import os

for k, v in {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "x",
             "OAUTH_ENCRYPTION_KEY": "test-oauth-encryption-key-32chars!!"}.items():
    os.environ.setdefault(k, v)

from app.services.brain_v1.analyzer import analyze
from app.services.brain_v1.normalize import clean, normalize

RX = "2026-10-13T10:00:00-06:00"


def _a(sender, subject, body):
    return analyze({"sender": sender, "subject": subject, "body_text": body, "received_at": RX, "labels": ["INBOX"],
                    "direction": "inbound"})


def test_meeting_explicit_date_sets_event_not_due():
    r = _a("pmo@empresa.example", "Reunión de seguimiento proyecto Atlas",
           "Jorge propone revisar avances el 28 de octubre de 2026 a las 10:00 en la sala 3.")
    assert r.dates.event_at.startswith("2026-10-28T10:00") and r.dates.due_at is None
    assert r.rule != "ambiguous" and r.area == "trabajo"


def test_school_meeting_and_hotel_and_english_flight():
    assert _a("avisos@colegio.example", "Junta de padres de familia",
              "La junta del grupo 3B será el 2026-10-18 a las 18:00.").dates.event_at.startswith("2026-10-18")
    assert _a("reservas@hotel.example", "Tu reservación en Hotel Brisa",
              "Te esperamos el 9 de noviembre de 2026. Check-in a partir de las 15:00.").dates.event_at.startswith("2026-11-09")
    r = _a("bookings@air.example", "Booking confirmation", "Your flight SW150 departs on December 19, 2026 at 9:40 AM.")
    assert r.dates.event_at.startswith("2026-12-19T09:40") and r.area == "viajes"


def test_relative_event_dates_are_never_invented():
    for body in ("Tu mesa para 4 quedó confirmada para el viernes a las 20:30.", "La reunión es mañana a las 10:00.",
                 "Your meeting is next monday."):
        assert _a("reservas@lugar.example", "Reservación confirmada", body).dates.event_at is None


def test_quoted_header_is_not_event_date():
    r = _a("x@hotel.example", "Fwd: Tu reservación en Hotel Brisa",
           "Te reenvío.\nEl 1 oct 2026, Ana escribió:\n> Te esperamos el 5 de diciembre de 2026.")
    assert (r.dates.event_at or "").startswith("2026-12-05") or r.dates.event_at is None


def test_normalize_typos_homoglyphs_invisibles():
    assert normalize("Cargo no reonocido") == "cargo no reconocido"
    assert normalize("Contraseña mdificda") == "contrasena modificada"
    assert clean("pаs\u200bsword") == "password"  # 'а' cirílica + ancho cero


def test_security_flag_survives_typos_and_keeps_area():
    r = _a("alertas@banco.example", "Cargo no reonocido en tu tarjeta",
           "Detectamos un caargo de $1,238.35 MXN que no oiincide con tus patronees. Si no lo reconoces, bloquea tu tarjeta desde la app oficial.")
    assert r.security_flag == "N1" and r.area == "dinero"
    r = _a("no-reply@nube.example", "Contraseña mdificda", "La contraeña de tu cueenta se cambió correctamente.")
    assert r.security_flag and r.area is not None


def test_clean_text_unchanged_path():
    r = _a("amigo@correo.example", "Hola", "Nos vemos pronto, saludos.")
    assert r.text_normalized is False
