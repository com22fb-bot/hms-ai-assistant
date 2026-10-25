"""Regresión de la auditoría fase 1 (issue #195).

Tipo: UNITARIAS. Cliente Supabase FALSO en memoria, datos sintéticos, sin red.
Ninguna prueba se ejecuta contra servicios reales.

Reproduce el flujo de safe_case_classifier.classify_pending_messages:
1) _find_case_for_message (asociación) y 2) classify_message (clasificación).
Las expectativas siguen las reglas A–G de Héctor; no se ajustaron para pasar.
Los escenarios fuera del alcance P0 (regla C de 3 días y regla E de bandeja
técnica) están marcados como xfail(strict=True): fallan hoy y lo documentan.
"""
from __future__ import annotations

import inspect
import os

os.environ.setdefault("SUPABASE_URL", "http://127.0.0.1:9")
os.environ.setdefault("SUPABASE_SECRET_KEY", "dummy-unit-test")
os.environ["BRAIN_V1_ENABLED"] = "0"

import pytest

from app.services import case_engine as ce
from app.services import safe_case_classifier as scc

pytestmark = pytest.mark.unit

OWN = ["hsalcidor@yahoo.com", "hmcelinfo@gmail.com"]  # confirmadas por Héctor


class _Q:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        if col.startswith("metadata->>"):
            key = col.split(">>")[1]
            self.rows = [r for r in self.rows if (r.get("metadata") or {}).get(key) == val]
        else:
            self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def gte(self, col, val):
        self.rows = [r for r in self.rows if str(r.get(col, "")) >= val]
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self):
        class R:
            pass
        r = R()
        r.data = self.rows
        return r


class FakeClient:
    def __init__(self, cases=(), msgs=(), links=()):
        self.t = {"intelligent_cases": list(cases), "communication_messages": list(msgs), "case_messages": list(links)}

    def table(self, name):
        return _Q(self.t.get(name, []))


def _supported(fn, kwargs):
    params = inspect.signature(fn).parameters
    return {k: v for k, v in kwargs.items() if k in params}


def msg(sender, subject, body, labels=("INBOX",), to=("hsalcidor@yahoo.com",), **kw):
    d = {"id": "m-x", "sender": sender, "subject": subject, "body_text": body, "labels": list(labels),
         "recipients": list(to), "is_unread": True, "thread_id": kw.pop("thread_id", "t-new")}
    d.update(kw)
    return d


def case(cid, subject, *, status="in_progress", thread="t-old", requester=None, summary="", event_key=None):
    return {"id": cid, "account_id": "acc-y", "workspace_id": "w", "primary_thread_id": thread,
            "title": subject, "summary": summary, "normalized_subject": ce.normalize_subject(subject),
            "requester_email": requester, "status": status,
            "metadata": {"event_key": event_key} if event_key else {}, "last_activity_at": "2026-10-01"}


def run(m, client=None, own=None):
    """Asociación + clasificación como en classify_pending_messages."""
    client = client or FakeClient()
    _, sender_email = ce._sender_parts(m.get("sender"))
    found = ce._find_case_for_message(**_supported(ce._find_case_for_message, dict(
        client=client, account_id="acc-y", thread_id=m.get("thread_id"),
        normalized_subject=ce.normalize_subject(m.get("subject")), workspace_id="w",
        reply_ids=ce.message_reply_ids(m) if hasattr(ce, "message_reply_ids") else None,
        sender_email=sender_email, evidence_text=f"{m.get('subject')}\n{m.get('body_text')}",
    )))
    cat, score, reason, actionable = scc.classify_message(**_supported(scc.classify_message, dict(
        message=m, existing_case=found, own_addresses=set(own) if own else None)))
    return {"case": found["id"] if found else None, "cat": cat, "actionable": actionable, "reason": reason}


G = "no-reply@accounts.google.com"


# --- Regla A/F: seguridad -------------------------------------------------
def test_e01_google_pide_confirmar_actividad_crea_caso():
    r = run(msg(G, "Alerta de seguridad", "Detectamos un inicio de sesión nuevo. ¿Fuiste tú? Confirma la actividad."))
    assert r["actionable"] and r["cat"] == "action_required"


def test_e02_google_informativa_queda_aviso():
    r = run(msg(G, "Alerta de seguridad", "Se otorgó acceso a una app a tu cuenta. No necesitas hacer nada."))
    assert not r["actionable"] and r["cat"] == "notice"


def test_e11_login_informativo_no_es_caso_ni_phishing():
    r = run(msg(G, "Nuevo inicio de sesión", "Se inició sesión desde Windows. Si fuiste tú, no necesitas hacer nada."))
    assert not r["actionable"] and r["cat"] == "notice"


def test_e12_login_sospechoso_crea_caso():
    r = run(msg(G, "Actividad sospechosa", "Bloqueamos un intento de inicio de sesión sospechoso. Revisa la actividad y cambia tu contraseña."))
    assert r["actionable"] and r["cat"] == "action_required"


def test_extra_english_was_this_you():
    r = run(msg(G, "Security alert", "New sign-in on your account. Was this you? Confirm it was you."))
    assert r["actionable"]


def test_extra_informativo_no_anula_accion():
    # Contiene texto informativo y además pide confirmar: gana la acción.
    r = run(msg(G, "Alerta de seguridad", "No necesitas hacer nada si reconoces esto. ¿Fuiste tú? Confirma la actividad."))
    assert r["actionable"]


def test_extra_no_todo_mensaje_de_seguridad_es_caso():
    r = run(msg(G, "Alerta de seguridad", "Se cambió la configuración de recuperación de tu cuenta."))
    assert not r["actionable"]


# --- Regla B: recibos -----------------------------------------------------
def test_e03_recibo_pagado_sin_caso_previo():
    r = run(msg("facturacion@proveedor-x.mx", "Recibo de pago", "Tu pago fue recibido. Saldo $0.00. Pagada."))
    assert not r["actionable"]


def test_e04_recibo_pagado_con_caso_de_cargo_fallido_misma_referencia():
    fail = case("C-fail", "Cargo fallido", requester="facturacion@proveedor-x.mx", summary="Cargo fallido referencia TX-123456")
    r = run(msg("facturacion@proveedor-x.mx", "Cargo fallido", "Pago recibido, referencia TX-123456. Pagada."), FakeClient([fail]))
    assert r["case"] == "C-fail"            # se vincula por evidencia (remitente + referencia)
    assert r["cat"] != "action_required"    # no se vuelve acción pendiente


def test_e05_recibo_de_otra_entidad_mismo_asunto_no_se_asocia():
    r = run(msg("cobros@otra-entidad.mx", "Pago", "Pago recibido ref 777777."),
            FakeClient([case("C-f2", "Pago", requester="facturacion@proveedor-x.mx", summary="ref 123456")]))
    assert r["case"] is None


# --- Regla C: enviados ----------------------------------------------------
def test_e06_enviado_con_peticion_y_respuesta_antes_de_2_dias():
    r = run(msg("hsalcidor@yahoo.com", "Cotización", "¿Me envías la cotización?", labels=("SENT",), to=("cliente@ext.com",)))
    assert not r["actionable"]


def test_e07_dia2_sin_caso():
    r = run(msg("hsalcidor@yahoo.com", "Cotización", "¿Me envías la cotización? Por favor confirma.",
                labels=("SENT",), to=("cliente@ext.com",), days_without_reply=2))
    assert not r["actionable"]  # aprueba de forma trivial: no existe lógica de días


@pytest.mark.xfail(strict=True, reason="Regla C (3 días naturales) no implementada; fuera de alcance P0.")
@pytest.mark.parametrize("days", [3, 4])
def test_e07_dias_3_y_4_crea_caso(days):
    r = run(msg("hsalcidor@yahoo.com", "Cotización", "¿Me envías la cotización? Por favor confirma.",
                labels=("SENT",), to=("cliente@ext.com",), days_without_reply=days))
    assert r["actionable"]


def test_e08_enviado_sin_peticion():
    r = run(msg("hsalcidor@yahoo.com", "Hola", "Te comparto la foto.", labels=("SENT",), to=("amigo@ext.com",)))
    assert not r["actionable"]


# --- Regla D: direcciones propias ----------------------------------------
def test_e09a_entre_buzones_propios_no_es_externo():
    r = run(msg("hsalcidor@yahoo.com", "Pendiente", "Por favor revisa y paga la factura antes del viernes, urgente.",
                to=("hmcelinfo@gmail.com",)), own=OWN)
    assert not r["actionable"]


def test_e09b_nota_propia_mayusculas_espacios():
    r = run(msg("  HSalcidor@YAHOO.com ", "Nota", "Por favor paga la factura urgente.", labels=("SENT", "INBOX")), own=OWN)
    assert not r["actionable"]


def test_extra_gmail_normalizacion_solo_gmail():
    from app.services import mail_direction as md
    assert md.normalize_address("H.McelInfo+x@Gmail.com") == "hmcelinfo@gmail.com"
    assert md.normalize_address("h.salcidor@yahoo.com") != "hsalcidor@yahoo.com"
    assert md.normalize_address("hsalcidor+x@yahoo.com") != "hsalcidor@yahoo.com"


def test_extra_tercero_no_es_propio():
    # Mismo texto que e09a (que sí supera el umbral de solicitud) para que la
    # única diferencia sea el remitente: dirección no confirmada = externa.
    r = run(msg("ahmcelinfo@gmail.com", "Pendiente", "Por favor revisa y paga la factura antes del viernes, urgente.",
                to=("hmcelinfo@gmail.com",)), own=OWN)
    assert r["actionable"]


# --- Regla E: técnicas ----------------------------------------------------
def test_e10a_railway_y_ci_no_crean_caso():
    assert not run(msg("notifications@railway.app", "Deploy failed", "Your deployment failed."))["actionable"]
    assert not run(msg("notifications@github.com", "Run failed: CI", "The workflow run failed."))["actionable"]


@pytest.mark.xfail(strict=True, reason="Regla E (bandeja técnica) no implementada; fuera de alcance P0.")
def test_e10b_respaldo_fallido_no_crea_caso_de_usuario():
    assert not run(msg("backup@servidor.mx", "Respaldo fallido", "El respaldo nocturno falló, por favor revisa urgente."))["actionable"]


# --- Regla G: cancelaciones ----------------------------------------------
def test_e13_cancelacion_relacionada_no_es_accion_pendiente():
    sub = case("C-sub", "Suscripción cancelada", requester="info@streaming.example", summary="Suscripción cuenta 98765")
    r = run(msg("info@streaming.example", "Suscripción cancelada", "Tu suscripción cuenta 98765 fue cancelada."), FakeClient([sub]))
    assert r["case"] == "C-sub" and r["cat"] != "action_required"


def test_e14_cancelacion_ajena_mismo_asunto_no_se_asocia():
    r = run(msg("info@streaming.example", "Cancelación confirmada", "Tu suscripción fue cancelada."),
            FakeClient([case("C-gym", "Cancelación confirmada", requester="socios@gym.example")]))
    assert r["case"] is None


# --- Asociación -----------------------------------------------------------
def test_e15_dos_facturas_distintas_mismo_asunto():
    a = case("C-A", "Factura disponible", requester="facturas@cfe.example", summary="Factura folio 111111")
    r = run(msg("facturas@cfe.example", "Factura disponible", "Factura folio 222222 por $500.00"), FakeClient([a]))
    assert r["case"] is None


def test_extra_misma_factura_mismo_folio_si_se_asocia():
    a = case("C-A", "Factura disponible", requester="facturas@cfe.example", summary="Factura folio 111111")
    r = run(msg("facturas@cfe.example", "Factura disponible", "Recordatorio factura folio 111111"), FakeClient([a]))
    assert r["case"] == "C-A"


def test_e16_coincidencia_con_caso_cerrado_no_reabre():
    r = run(msg("x@ext.example", "Re: Factura disponible", "gracias"),
            FakeClient([case("C-closed", "Factura disponible", status="closed")]))
    assert r["case"] is None


def test_e17a_respuesta_mismo_hilo():
    r = run(msg("x@ext.example", "Re: otro", "ok", thread_id="t-1"), FakeClient([case("C-h", "Asunto X", thread="t-1")]))
    assert r["case"] == "C-h"


def test_e17b_entrante_con_in_reply_to_sin_hilo():
    c = FakeClient([case("C-r", "Y", thread="t-1")],
                   msgs=[{"id": "m1", "account_id": "acc-y", "internet_message_id": "<p1@x>"}],
                   links=[{"message_id": "m1", "case_id": "C-r"}])
    r = run(msg("x@ext.example", "otro asunto", "ok", thread_id=None, in_reply_to="<p1@x>"), c)
    assert r["case"] == "C-r"


def test_e18_generico_sin_datos_no_se_asocia():
    r = run(msg("persona@ext.example", "Hola", "ok"), FakeClient([case("C-g", "Hola", requester="persona@ext.example")]))
    assert r["case"] is None and not r["actionable"]
