"""CONTACTS_V1 · F1 · Migración en Postgres LOCAL aislado (no Supabase): restricciones,
integridad, RLS/grants, cascadas, idempotencia y rollback. Datos sintéticos.
Se omite salvo R3_TEST_ALLOW_LOCAL_DB=1 y R3_TEST_DSN a localhost (ver conftest)."""
from __future__ import annotations

import uuid

import pytest
from psycopg import errors as pg

from tests.db.conftest import PREP
from tests.db.world import one

MIGRATION = "20261127_001_contacts_v1_identity.sql"
ROLLBACK = PREP.parent / "rollbacks" / "20261127_001_contacts_v1_identity_rollback.sql"
NEW = ("message_participants", "contact_addresses", "own_address_aliases")


def _u():
    return str(uuid.uuid4())


@pytest.fixture()
def world(db):
    db.execute((PREP / MIGRATION).read_text())
    w = {"ws": _u(), "ws2": _u(), "p": _u()}
    db.execute("insert into profiles (id, email) values (%s, 'prueba@example.test')", (w["p"],))
    for ws in (w["ws"], w["ws2"]):
        db.execute("insert into workspaces (id, name) values (%s, 'sintetico')", (ws,))
    w["acc"], w["acc2"] = _u(), _u()
    db.execute("insert into communication_accounts (id, workspace_id, provider, email) values "
               "(%s,%s,'google','yo@example.test'), (%s,%s,'google','otra@example.test')",
               (w["acc"], w["ws"], w["acc2"], w["ws2"]))
    w["m"], w["m2"] = _u(), _u()
    db.execute("insert into communication_messages (id, account_id, external_message_id, sender, direction, received_at)"
               " values (%s,%s,'e1','ana@cliente.test','inbound',now()), (%s,%s,'e2','b@x.test','inbound',now())",
               (w["m"], w["acc"], w["m2"], w["acc2"]))
    return w


def part(db, w, *, role="from", position=0, norm="ana@cliente.test", status="ok", own=False,
         message=None, account=None, ws=None):
    db.execute(
        "insert into message_participants (message_id, workspace_id, account_id, role, position, address_original,"
        " address_norm, parse_status, source, direction, occurred_at, is_own)"
        " values (%s,%s,%s,%s,%s,'Original',%s,%s,'fixture','inbound',now(),%s)",
        (message or w["m"], ws or w["ws"], account or w["acc"], role, position, norm, status, own))




def test_migracion_idempotente_y_rls(db, world):
    db.execute((PREP / MIGRATION).read_text())          # segunda aplicación: sin error
    for t in NEW:
        assert one(db, "select relrowsecurity from pg_class where oid = %s::regclass", f"public.{t}") is True
        assert one(db, "select count(*) from pg_policies where tablename = %s", t) == 0
        for role in ("anon", "authenticated"):
            assert one(db, "select has_table_privilege(%s, %s, 'select')", role, f"public.{t}") is False
            assert one(db, "select has_table_privilege(%s, %s, 'insert')", role, f"public.{t}") is False
        assert one(db, "select has_table_privilege('service_role', %s, 'insert')", f"public.{t}") is True


def test_authenticated_no_lee_ni_escribe(db, world):
    part(db, world)
    db.execute("set role authenticated")
    try:
        with pytest.raises(pg.InsufficientPrivilege):
            db.execute("select count(*) from message_participants")
    finally:
        db.execute("reset role")
    db.execute("set role anon")
    try:
        with pytest.raises(pg.InsufficientPrivilege):
            db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s, 'a@x.test')",
                       (world["ws"],))
    finally:
        db.execute("reset role")


def test_service_role_escribe(db, world):
    db.execute("set role service_role")
    try:
        part(db, world)
        db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,'ana@cliente.test')",
                   (world["ws"],))
    finally:
        db.execute("reset role")
    assert one(db, "select domain from contact_addresses") == "cliente.test"


@pytest.mark.parametrize("kwargs", [
    {"norm": None, "status": "ok"},                    # ok sin dirección
    {"norm": "a@x.test", "status": "ambiguous"},       # no confiable con dirección
    {"norm": None, "status": "invalid", "own": True},  # no confiable marcada propia
    {"norm": "Ana@X.test"},                            # sin normalizar
    {"norm": "ana x@x.test"},
    {"norm": "a@localhost"},
    {"norm": "juan.perez@gmail.com"},                  # Gmail sin canonizar (Bugbot #219)
    {"norm": "juan+x@gmail.com"},
    {"norm": "juan@googlemail.com"},
    {"role": "nombre"},
    {"status": "raro", "norm": None},
])
def test_checks_de_participantes(db, world, kwargs):
    with pytest.raises(pg.CheckViolation):
        part(db, world, **kwargs)


def test_unicidad_y_duplicados(db, world):
    part(db, world, role="to", position=0, norm="a@x.test")
    with pytest.raises(pg.UniqueViolation):
        part(db, world, role="to", position=1, norm="a@x.test")      # misma dirección, mismo rol
    with pytest.raises(pg.UniqueViolation):
        part(db, world, role="to", position=0, norm="b@x.test")      # misma posición
    part(db, world, role="cc", position=0, norm="a@x.test")          # otro rol: permitido
    part(db, world, role="to", position=1, norm=None, status="invalid")
    part(db, world, role="to", position=2, norm=None, status="ambiguous")  # varios no confiables
    db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,'a@x.test')", (world["ws"],))
    with pytest.raises(pg.UniqueViolation):
        db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,'a@x.test')",
                   (world["ws"],))
    db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,'a@x.test')", (world["ws2"],))


def test_guarda_de_integridad_mensaje_cuenta_workspace(db, world):
    with pytest.raises(pg.ForeignKeyViolation):
        part(db, world, ws=world["ws2"])                             # workspace ajeno
    with pytest.raises(pg.ForeignKeyViolation):
        part(db, world, account=world["acc2"])                       # cuenta de otro workspace
    with pytest.raises(pg.ForeignKeyViolation):
        part(db, world, message=world["m2"])                         # mensaje de otra cuenta
    part(db, world)
    with pytest.raises(pg.ForeignKeyViolation):
        db.execute("update message_participants set workspace_id = %s", (world["ws2"],))


def test_cascadas(db, world):
    part(db, world)
    db.execute("delete from communication_messages where id = %s", (world["m"],))
    assert one(db, "select count(*) from message_participants") == 0
    part(db, world, message=world["m2"], account=world["acc2"], ws=world["ws2"], norm="b@x.test")
    db.execute("delete from communication_accounts where id = %s", (world["acc2"],))
    assert one(db, "select count(*) from message_participants") == 0
    ws3 = _u()
    db.execute("insert into workspaces (id, name) values (%s, 'sin cuentas')", (ws3,))
    db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,'a@x.test')", (ws3,))
    db.execute("insert into own_address_aliases (workspace_id, address_norm, status) values (%s,'yo@alias.test','detected')",
               (ws3,))
    db.execute("delete from workspaces where id = %s", (ws3,))
    assert one(db, "select count(*) from contact_addresses where workspace_id = %s", ws3) == 0
    assert one(db, "select count(*) from own_address_aliases where workspace_id = %s", ws3) == 0


def test_alias_exige_decision_con_fecha(db, world):
    ins = "insert into own_address_aliases (workspace_id, address_norm, status, decided_by, decided_at) values (%s,%s,%s,%s,%s)"
    db.execute(ins, (world["ws"], "a1@alias.test", "detected", None, None))
    with pytest.raises(pg.CheckViolation):
        db.execute(ins, (world["ws"], "a2@alias.test", "confirmed", world["p"], None))
    with pytest.raises(pg.CheckViolation):
        db.execute(ins, (world["ws"], "a3@alias.test", "detected", None, "2026-11-27"))
    with pytest.raises(pg.CheckViolation):
        db.execute(ins, (world["ws"], "a4@alias.test", "propio", None, "2026-11-27"))
    db.execute("update own_address_aliases set status='confirmed', decided_by=%s, decided_at=now() "
               "where address_norm='a1@alias.test'", (world["p"],))
    db.execute("delete from profiles where id = %s", (world["p"],))   # la decisión sobrevive
    assert one(db, "select status from own_address_aliases where address_norm='a1@alias.test'") == "confirmed"


def test_estadisticas_no_negativas_y_orden_temporal(db, world):
    with pytest.raises(pg.CheckViolation):
        db.execute("insert into contact_addresses (workspace_id, address_norm, received_count) values (%s,'a@x.test',-1)",
                   (world["ws"],))
    with pytest.raises(pg.CheckViolation):
        db.execute("insert into contact_addresses (workspace_id, address_norm, first_at, last_at) "
                   "values (%s,'a@x.test','2026-11-02','2026-11-01')", (world["ws"],))


def test_no_altera_tablas_existentes_y_rollback(db, world):
    before = dict(db.execute("select table_name, count(*) from information_schema.columns "
                             "where table_schema='public' and table_name not in "
                             "('message_participants','contact_addresses','own_address_aliases') "
                             "group by table_name").fetchall())
    msgs = one(db, "select count(*) from communication_messages")
    db.execute(ROLLBACK.read_text())
    for t in NEW:
        assert one(db, "select to_regclass(%s)", f"public.{t}") is None
    assert one(db, "select count(*) from pg_proc where proname = 'contacts_v1_participant_guard'") == 0
    after = dict(db.execute("select table_name, count(*) from information_schema.columns "
                            "where table_schema='public' group by table_name").fetchall())
    assert after == before and one(db, "select count(*) from communication_messages") == msgs


def test_salida_de_contact_identity_cumple_el_check_de_bd(db, world):
    """La normalización de F0 y el CHECK de F1 coinciden (sin divergencias Python/Postgres)."""
    from app.services import contact_identity as ci
    from app.services.contact_registry_repository import is_valid_norm

    raws = ['"José" <JOSÉ@Ejemplo.MX>', "x@München.de", "o'brien@x.test", "Ana.Lopez+x@Empresa.MX",
            "Juan.Perez+banco@GMail.com", '"aviso@banamex.com.mx, Soporte" <x@atacante.test>', "a_b-c@sub.dominio.test"]
    for raw in raws:
        norm = ci.identity_from_stored_sender(raw).address_norm
        assert norm and is_valid_norm(norm)
        db.execute("insert into contact_addresses (workspace_id, address_norm) values (%s,%s)", (world["ws"], norm))
    assert one(db, "select count(*) from contact_addresses") == len(raws)


@pytest.mark.parametrize("table,extra", [("contact_addresses", ""), ("own_address_aliases", "detected")])
@pytest.mark.parametrize("norm", ["juan.perez@gmail.com", "juan+x@gmail.com", "juan@googlemail.com"])
def test_gmail_no_canonico_rechazado_en_todas_las_tablas(db, world, table, extra, norm):
    with pytest.raises(pg.CheckViolation):
        if extra:
            db.execute(f"insert into {table} (workspace_id, address_norm, status) values (%s,%s,%s)",
                       (world["ws"], norm, extra))
        else:
            db.execute(f"insert into {table} (workspace_id, address_norm) values (%s,%s)", (world["ws"], norm))
