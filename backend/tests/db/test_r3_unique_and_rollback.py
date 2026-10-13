"""Índice único de buzón vivo (003) y rollback seguro con corridas simultáneas (001)."""
from __future__ import annotations

import os
import threading
import uuid

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from tests.db.conftest import UNIQUE_MAILBOX
from tests.db.world import one, run


def _other_conn(db):
    params = dict(conninfo_to_dict(os.environ["R3_TEST_DSN"]), dbname=db.info.dbname)
    return psycopg.connect(" ".join(f"{k}={v}" for k, v in params.items()), autocommit=True)


def _ws(db):
    wid = str(uuid.uuid4())
    db.execute("insert into workspaces (id, name) values (%s, 'w')", (wid,))
    return wid


def _acc(db, ws, provider="google", pid="G", email="a@example.test", status="active"):
    return one(db, "insert into communication_accounts (workspace_id, provider, provider_account_id, email, status) "
                   "values (%s,%s,%s,%s,%s) returning id::text", ws, provider, pid, email, status)


# ------------------------------------------------------------------ índice único
def test_indice_un_buzon_vivo_por_proveedor_y_direccion(db):
    run(db, UNIQUE_MAILBOX)
    w1, w2 = _ws(db), _ws(db)
    _acc(db, w1, email="a@example.test")
    for email, status in (("  A@Example.TEST ", "active"), ("a@example.test", "needs_reauth")):
        with pytest.raises(psycopg.errors.UniqueViolation):
            _acc(db, w2, email=email, status=status, pid="G2")
    # inactivas / superseded / otro proveedor / otra dirección: permitidas
    _acc(db, w2, status="inactive")
    _acc(db, w2, status="superseded")
    _acc(db, w2, provider="microsoft")
    _acc(db, w2, email="b@example.test")
    # sin email: la clave es provider_account_id
    _acc(db, w1, provider="imap", pid="X@Y.Z", email=None)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _acc(db, w2, provider="imap", pid="x@y.z", email="")
    assert one(db, "select address_key from communication_accounts where provider='imap'") == "x@y.z"


def test_indice_falla_si_hay_duplicados_vivos(db):
    w1, w2 = _ws(db), _ws(db)
    _acc(db, w1)
    _acc(db, w2)
    with pytest.raises(psycopg.errors.UniqueViolation):
        run(db, UNIQUE_MAILBOX)


def test_inserciones_concurrentes_solo_una_gana(db):
    run(db, UNIQUE_MAILBOX)
    w1, w2 = _ws(db), _ws(db)
    other = _other_conn(db)
    try:
        db.execute("begin")
        _acc(db, w1)
        errors: list[Exception] = []

        def second():
            try:
                _acc(other, w2)
            except Exception as error:  # noqa: BLE001
                errors.append(error)

        t = threading.Thread(target=second)
        t.start()
        t.join(0.5)
        assert t.is_alive()          # la segunda espera al índice
        db.execute("commit")
        t.join(5)
        assert len(errors) == 1 and isinstance(errors[0], psycopg.errors.UniqueViolation)
    finally:
        other.close()
    assert one(db, "select count(*) from communication_accounts where status='active'") == 1


# ------------------------------------------------------------------ rollback
def _logged_update(db, acc):
    op = one(db, "insert into ops_r3_operation (script) values ('prueba') returning op_id::text")
    before = one(db, "select to_jsonb(a) from communication_accounts a where id=%s", acc)
    db.execute("update communication_accounts set status='superseded', display_name='x' where id=%s", (acc,))
    db.execute("select ops_r3_log(%s, 'communication_accounts', %s, 'update', %s)", (op, acc, psycopg.types.json.Jsonb(before)))
    return op


def test_rollback_restaura_con_columna_generada(db):
    run(db, UNIQUE_MAILBOX)
    acc = _acc(db, _ws(db))
    before = one(db, "select md5(to_jsonb(a)::text) from communication_accounts a where id=%s", acc)
    op = _logged_update(db, acc)
    res = dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall())
    assert res == {"reverted": 1}
    assert one(db, "select md5(to_jsonb(a)::text) from communication_accounts a where id=%s", acc) == before


def test_rollback_de_borrado_con_columna_generada(db):
    run(db, UNIQUE_MAILBOX)
    acc = _acc(db, _ws(db))
    op = one(db, "insert into ops_r3_operation (script) values ('prueba') returning op_id::text")
    before = one(db, "select to_jsonb(a) from communication_accounts a where id=%s", acc)
    db.execute("delete from communication_accounts where id=%s", (acc,))
    db.execute("select ops_r3_log(%s, 'communication_accounts', %s, 'delete', %s)", (op, acc, psycopg.types.json.Jsonb(before)))
    assert dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall()) == {"reverted": 1}
    assert one(db, "select address_key from communication_accounts where id=%s", acc) == "a@example.test"


def test_rollback_dos_veces_no_revierte_dos_veces(db):
    acc = _acc(db, _ws(db))
    op = _logged_update(db, acc)
    db.execute("select * from ops_r3_rollback(%s)", (op,))
    db.execute("update communication_accounts set display_name='posterior' where id=%s", (acc,))
    res = dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall())
    assert res == {"reverted": 1}
    assert one(db, "select count(*) from ops_r3_rollback_report where op_id=%s", op) == 1
    assert one(db, "select display_name from communication_accounts where id=%s", acc) == "posterior"


def test_rollback_simultaneo_solo_uno_actua(db):
    acc = _acc(db, _ws(db))
    op = _logged_update(db, acc)
    other = _other_conn(db)
    try:
        db.execute("begin")
        db.execute("select * from ops_r3_rollback(%s)", (op,))
        out: list = []
        t = threading.Thread(target=lambda: out.append(
            dict(other.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall())))
        t.start()
        t.join(0.5)
        assert t.is_alive()          # espera el candado
        db.execute("commit")
        t.join(10)
        assert out == [{"reverted": 1}]
    finally:
        other.close()
    assert one(db, "select count(*) from ops_r3_rollback_report where op_id=%s", op) == 1
    assert one(db, "select status from ops_r3_operation where op_id=%s", op) == "rolled_back"


def test_rollback_respeta_cambio_posterior(db):
    acc = _acc(db, _ws(db))
    op = _logged_update(db, acc)
    db.execute("update communication_accounts set status='active' where id=%s", (acc,))   # reconexión
    assert dict(db.execute("select * from ops_r3_rollback(%s)", (op,)).fetchall()) == {"skipped_changed": 1}
    assert one(db, "select status from communication_accounts where id=%s", acc) == "active"


def test_rollback_operacion_inexistente(db):
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("select * from ops_r3_rollback(gen_random_uuid())")
