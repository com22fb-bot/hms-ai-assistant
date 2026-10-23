"""Criterios de aceptación de ASTRA para el semáforo (1–6 backend; 7 y 8 en frontend)."""
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import health_eval as h

NOW = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)


def ok(cid, critical=True):
    return h.result(cid, cid, critical, "ok", "ok", "ok", data_at=NOW.isoformat())


def build(**over):
    base = {c: (lambda c=c, crit=crit: ok(c, crit)) for c, crit in
            [("api", True), ("database", True), ("config", True), ("backup", True), ("frontend", True),
             ("railway", False), ("cloudflare", False)]}
    base.update(over)
    meta = {c: (c, c in ("api", "database", "config", "backup", "frontend")) for c in base}
    return lambda: (base, meta)


def ev(**over):
    h._cache.clear()
    return h.evaluate(build(**over), None, force=True)


# 1. Un HTTP 200 no oculta una dependencia crítica fallida
def test_200_del_sitio_no_oculta_base_caida():
    class Broken:
        def table(self, *_):
            raise RuntimeError("db down")
    r = ev(frontend=lambda: h.check_site("frontend", "App", "u", True, getter=lambda u: (200, 10, {}, None)),
           database=lambda: h.check_database(Broken()))
    assert r["overall"]["state"] == "ROJO"


# 2. «Not Authorized» de Railway no es caída confirmada
def test_not_authorized_es_permiso_no_caida():
    r = ev(railway=lambda: h.check_railway(lambda: {"available": False, "status": "error", "message": "Not Authorized"}))
    rw = next(c for c in r["checks"] if c["id"] == "railway")
    assert rw["kind"] == "permiso" and rw["status"] == "sin_verificar"
    assert r["overall"]["state"] == "AMARILLO"
    assert h.classify_provider_error("Not Authorized") == "permiso"
    assert h.classify_provider_error(http_status=503) == "proveedor_caido"
    assert h.classify_provider_error(exc=httpx.ReadTimeout("t")) == "timeout"


# 3. Un fallo crítico propio activa rojo
def test_config_critica_rota_es_rojo(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "")
    r = ev(config=h.check_config)
    assert r["overall"]["state"] == "ROJO"


def test_respaldo_vencido_mas_de_54h_es_rojo():
    class C:
        def table(self, *_): return self
        def select(self, *_): return self
        def eq(self, *_): return self
        def order(self, *_, **__): return self
        def limit(self, *_): return self
        def execute(self):
            class R: data = [{"occurred_at": (NOW - timedelta(hours=60)).isoformat(), "meta": {"kind": "diario", "result": "ok", "verified": True}}]
            return R()
    c = h.check_backup(C(), now=NOW)
    assert c["status"] == "falla" and h.overall([c])["state"] == "ROJO"


# 4. Degradación externa no crítica => amarillo si el núcleo funciona
def test_proveedor_externo_caido_es_amarillo():
    r = ev(cloudflare=lambda: h.check_cloudflare(lambda: {"available": False, "status": "error", "message": "HTTP 503"}))
    assert r["overall"]["state"] == "AMARILLO"


# 5. Verde solo con todo lo crítico verificado
def test_verde_solo_si_todo_ok():
    assert ev()["overall"]["state"] == "VERDE"


def test_timeout_nunca_es_verde(monkeypatch):
    monkeypatch.setattr(h, "CHECK_TIMEOUT_S", 0.2)
    checks = h.run_checks({"database": lambda: (time.sleep(1), ok("database"))[1]}, {"database": ("db", True)}, timeout=0.2)
    assert checks[0]["status"] == "sin_verificar" and checks[0]["kind"] == "timeout"
    assert h.overall(checks)["state"] != "VERDE"


def test_chequeo_que_lanza_excepcion_no_es_verde():
    checks = h.run_checks({"x": lambda: 1 / 0}, {"x": ("x", True)})
    assert checks[0]["status"] == "sin_verificar" and h.overall(checks)["state"] == "AMARILLO"


# 6. Datos ausentes o vencidos no se presentan como válidos
def test_sin_muestras_no_hay_cero_falso():
    c = h.check_errors({"recent_15m": {"requests": 3, "errors_5xx": 0}})
    assert c["status"] == "sin_verificar" and c["kind"] == "sin_datos"


def test_respaldo_de_31h_es_vencido_no_ok():
    class C:
        def table(self, *_): return self
        def select(self, *_): return self
        def eq(self, *_): return self
        def order(self, *_, **__): return self
        def limit(self, *_): return self
        def execute(self):
            class R: data = [{"occurred_at": (NOW - timedelta(hours=31)).isoformat(), "meta": {"kind": "diario", "result": "ok", "verified": True}}]
            return R()
    c = h.check_backup(C(), now=NOW)
    assert c["status"] == "degradado" and c["kind"] == "vencido"


def test_runtime_sin_peticiones_devuelve_none():
    from app.services import runtime_metrics as rm
    assert rm._percentile([], 95) is None


def test_desafio_cloudflare_al_monitor_no_es_caida():
    c = h.check_site("landing", "L", "u", False, getter=lambda u: (403, 5, {"cf-mitigated": "challenge"}, None))
    assert c["kind"] == "monitoreo" and c["status"] == "sin_verificar"


# Recuperación verificable y deduplicación de incidentes
class FakeEvents:
    def __init__(self): self.rows, self._f, self._op = [], {}, None
    def table(self, _): self._f, self._op, self._payload = {}, "select", None; return self
    def select(self, *_): return self
    def eq(self, k, v): self._f[k] = v; return self
    def order(self, *_, **__): return self
    def limit(self, *_): return self
    def insert(self, row): self._op, self._payload = "insert", row; return self
    def update(self, row): self._op, self._payload = "update", row; return self
    def execute(self):
        class R: pass
        r = R()
        if self._op == "insert":
            row = {**self._payload, "id": str(len(self.rows) + 1)}; self.rows.append(row); r.data = [row]
        elif self._op == "update":
            for row in self.rows:
                if row["id"] == self._f.get("id"): row.update(self._payload)
            r.data = []
        else:
            r.data = [x for x in self.rows if all(x.get(k) == v for k, v in self._f.items())]
        return r


def test_incidente_deduplicado_y_recuperacion_con_3_ok_en_2_min():
    db = FakeEvents()
    bad = h.result("database", "DB", True, "falla", "falla_propia", "x")
    good = h.result("database", "DB", True, "ok", "ok", "ok")
    h.reconcile_incidents(db, [bad], NOW)
    h.reconcile_incidents(db, [bad], NOW + timedelta(seconds=30))
    assert len(db.rows) == 1  # sin alertas repetidas
    h.reconcile_incidents(db, [good], NOW + timedelta(seconds=60))
    h.reconcile_incidents(db, [good], NOW + timedelta(seconds=90))
    h.reconcile_incidents(db, [good], NOW + timedelta(seconds=120))
    assert db.rows[0]["status"] == "abierto"  # 3 OK pero solo 60 s: aún no
    h.reconcile_incidents(db, [good], NOW + timedelta(seconds=190))
    assert db.rows[0]["status"] == "resuelto" and db.rows[0]["meta"]["ok_streak"] == 4
    assert [t["to"] for t in db.rows[0]["meta"]["transitions"]] == ["falla", "recuperando", "resuelto"]


def test_recaida_reinicia_racha():
    db = FakeEvents()
    bad = h.result("backup", "B", True, "falla", "falla_propia", "x")
    good = h.result("backup", "B", True, "ok", "ok", "ok")
    h.reconcile_incidents(db, [bad], NOW)
    h.reconcile_incidents(db, [good], NOW + timedelta(seconds=30))
    h.reconcile_incidents(db, [bad], NOW + timedelta(seconds=60))
    assert db.rows[0]["meta"]["ok_streak"] == 0 and db.rows[0]["status"] == "abierto"


# Hallazgo de Héctor (23-oct 1:01 pm): todas las páginas 200 y Railway «Not Authorized» escondido en su tarjeta.
def test_paginas_200_y_railway_not_authorized_pone_amarillo_global():
    site = lambda cid, crit: (lambda: h.check_site(cid, cid, "u", crit, getter=lambda u: (200, 80, {}, None)))
    r = ev(frontend=site("frontend", True), landing=site("landing", False),
           railway=lambda: h.check_railway(lambda: {"available": False, "status": "error", "message": "Not Authorized"}))
    states = {c["id"]: c for c in r["checks"]}
    assert states["frontend"]["status"] == "ok" and states["landing"]["status"] == "ok"
    assert states["railway"]["kind"] == "permiso"  # monitoreo/permiso, no caída
    assert "No indica que el proveedor esté caído" in states["railway"]["hypothesis"]
    assert r["overall"]["state"] == "AMARILLO" and "Railway" in r["overall"]["reason"]


def test_railway_error_parcial_no_es_ok():
    from app.api import admin_perf
    class R:
        status_code = 200
        def json(self): return {"data": {"metrics": []}, "errors": [{"message": "Not Authorized"}]}
    import os
    os.environ["RAILWAY_METRICS_TOKEN"] = "fixture"
    orig = admin_perf.httpx.post
    admin_perf.httpx.post = lambda *a, **k: R()
    try:
        out = admin_perf._railway()
    finally:
        admin_perf.httpx.post = orig
        del os.environ["RAILWAY_METRICS_TOKEN"]
    assert out["available"] is False and out["kind"] == "permiso"


def test_token_de_proyecto_usa_su_cabecera(monkeypatch):
    from app.api import admin_perf
    monkeypatch.setenv("RAILWAY_METRICS_TOKEN", "fixture")
    assert admin_perf._railway_headers() == {"Project-Access-Token": "fixture"}
    monkeypatch.delenv("RAILWAY_METRICS_TOKEN")
    monkeypatch.setenv("RAILWAY_API_TOKEN", "fixture2")
    assert admin_perf._railway_headers() == {"Authorization": "Bearer fixture2"}
