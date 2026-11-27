from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import admin_perf
from app.services import payments_agenda as pa

EXPENSES = [
    {"id": "c", "servicio": "Cursor", "plan": "Pro", "monto": 20, "moneda": "USD", "periodicidad": "mensual",
     "proximo_cobro": "2026-12-07", "notas": "Renovación estimada el 7 de cada mes", "activo": True},
    {"id": "g", "servicio": "ChatGPT", "plan": "Go", "monto": 100, "moneda": "MXN", "periodicidad": "mensual",
     "proximo_cobro": "2026-12-09", "notas": "Fecha de cobro estimada", "activo": True},
    {"id": "r", "servicio": "Railway", "plan": "Hobby", "monto": 5, "moneda": "USD", "periodicidad": "mensual",
     "proximo_cobro": "2026-12-15", "notas": "", "activo": True},
    {"id": "d", "servicio": "Dominio donexto.com", "plan": "Registrar", "monto": 10.46, "moneda": "USD",
     "periodicidad": "anual", "proximo_cobro": "2027-08-07", "notas": "costo estimado", "activo": True},
    {"id": "n", "servicio": "n8n", "plan": "Starter", "monto": 24, "moneda": "USD", "periodicidad": "mensual",
     "proximo_cobro": "2026-12-01", "notas": "", "activo": True},
    {"id": "s", "servicio": "SuperGrok", "plan": "", "monto": 10, "moneda": "USD", "periodicidad": "unico",
     "proximo_cobro": None, "notas": "", "activo": True},
    {"id": "x", "servicio": "Viejo", "plan": "", "monto": 50, "moneda": "USD", "periodicidad": "mensual",
     "proximo_cobro": "2026-11-28", "notas": "", "activo": False},
]
FX = 19.696271
TODAY = date(2026, 11, 27)


def _agenda(**kw):
    return pa.build_payments_agenda(kw.get("rows", EXPENSES), kw.get("fx", FX), kw.get("today", TODAY))


def test_severity_bounds():
    assert [pa.severity_of(d) for d in (-2, 0, 3, 4, 14, 15, 60, 61)] == [
        "rojo", "rojo", "rojo", "naranja", "naranja", "verde", "verde", "luego"]


def test_today_uses_mexico_city_time():
    # 03:30 UTC del 28-nov = 21:30 del 27-nov en CDMX.
    assert pa.today_cdmx(datetime(2026, 11, 28, 3, 30, tzinfo=timezone.utc)) == date(2026, 11, 27)


def test_items_days_severity_and_money():
    a = _agenda()
    by = {(i["servicio"], i["on"]): i for i in a["items"]}
    cursor = by[("Cursor", "2026-12-07")]
    assert (cursor["days"], cursor["severity"], cursor["usd"], cursor["mxn"]) == (10, "naranja", 20.0, 393.93)
    assert cursor["estimated"] is True and "cursor.com" in cursor["action"]
    chatgpt = by[("ChatGPT", "2026-12-09")]
    assert (chatgpt["usd"], chatgpt["mxn"], chatgpt["severity"]) == (5.08, 100.0, "naranja")
    assert by[("Railway", "2026-12-15")]["severity"] == "verde"
    assert by[("Dominio donexto.com", "2027-08-07")]["severity"] == "luego"
    # Lo de tools_agenda que ya está en Mis gastos no se duplica.
    assert sum(1 for i in a["items"] if i["servicio"] == "Railway") == 1
    assert sum(1 for i in a["items"] if i["tipo"] == "renovación" and i["on"] == "2027-08-07") == 1
    assert [i["on"] for i in a["items"]] == sorted(i["on"] for i in a["items"])


def test_keys_are_free_and_excluded_ones_never_appear():
    a = _agenda()
    keys = [i for i in a["items"] if i["tipo"] == "llave"]
    assert {k["label"] for k in keys} >= {"GH_DISPATCH_TOKEN", "GH_BOT_TOKEN"}
    assert all(k["usd"] == 0 and k["mxn"] == 0 for k in keys)
    blob = repr(a).lower()
    assert "n8n" not in blob and "github_token_donexto" not in blob
    assert not any(i["servicio"] == "Viejo" for i in a["items"])


def test_monthly_total_matches_mis_gastos_rules():
    m = _agenda()["monthly"]
    # 20 + 5.08 + 5 + 10.46/12 (anual); sin pago único, inactivos ni n8n.
    assert m["usd"] == pytest.approx(30.95, abs=0.01)
    assert m["mxn"] == round(m["usd"] * FX, 2)
    assert m["parts"][0]["servicio"] == "Cursor"


def test_headline_and_overdue():
    a = _agenda()
    assert a["headline"] == "Nada vencido ni por vencer en 3 días"
    late = _agenda(today=date(2026, 12, 8))
    assert late["headline"] == "1 vencido(s)"
    cursor = next(i for i in late["items"] if i["servicio"] == "Cursor")
    assert (cursor["days"], cursor["severity"]) == (-1, "rojo")
    assert late["status"] == "rojo"


def test_fx_fallback_when_setting_missing():
    a = _agenda(fx=None)
    assert a["fx"]["usd_mxn"] == pa.FX_USD_MXN and a["fx"]["date"] == pa.FX_DATE
    assert _agenda()["fx"]["source"].startswith("Mis gastos")


def test_endpoint_requires_admin():
    with patch.object(admin_perf, "_require_admin", side_effect=HTTPException(status_code=403, detail="no")):
        with pytest.raises(HTTPException):
            admin_perf.admin_payments_agenda()


def test_endpoint_reads_only_and_builds_agenda():
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value.execute.return_value = MagicMock(data=EXPENSES)
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"value": "19.696271"}])
    with patch.object(admin_perf, "_require_admin"), \
            patch.object(admin_perf, "get_supabase_client", return_value=client), \
            patch.object(pa, "today_cdmx", return_value=TODAY):
        out = admin_perf.admin_payments_agenda()
    assert out["fx"]["usd_mxn"] == FX
    assert any(i["servicio"] == "Cursor" for i in out["items"])
    for verb in ("insert", "update", "delete", "upsert"):
        getattr(table, verb).assert_not_called()
