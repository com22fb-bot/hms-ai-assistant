"""Fixture de BD aislada para los ensayos de ronda 3.

Seguridad (lista blanca, no lista negra): solo se aceptan conexiones a
localhost / 127.0.0.1 / ::1 / socket Unix, a bases de administración
explícitamente permitidas, y con R3_TEST_ALLOW_LOCAL_DB=1. Cualquier otra
cosa se rechaza antes de conectar.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.conninfo import conninfo_to_dict  # noqa: E402

HERE = Path(__file__).parent
PREP = HERE.parents[2] / "supabase" / "migrations"
OPS_INFRA = "20261012_001_r3_ops_infra.sql"
ORPHAN_GUARDS = "20261012_002_r3_orphan_guards.sql"
UNIQUE_MAILBOX = "20261012_003_r3_unique_live_mailbox.sql"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWED_ADMIN_DBS = {"postgres", "r3_admin"}


class UnsafeDsn(ValueError):
    pass


def check_safe_dsn(dsn: str | None, env: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ if env is None else env
    if env.get("R3_TEST_ALLOW_LOCAL_DB") != "1":
        raise UnsafeDsn("falta R3_TEST_ALLOW_LOCAL_DB=1")
    if not dsn:
        raise UnsafeDsn("R3_TEST_DSN vacío")
    try:
        params = conninfo_to_dict(dsn)
    except Exception as error:  # noqa: BLE001
        raise UnsafeDsn("DSN ilegible") from error
    host = str(params.get("host") or "")
    hosts = [h for h in host.split(",") if h] or ["(socket)"]
    for h in hosts:
        if h == "(socket)" or h.startswith("/"):
            continue
        if h not in ALLOWED_HOSTS:
            raise UnsafeDsn(f"host no permitido: {h}")
    if params.get("hostaddr") and params["hostaddr"] not in {"127.0.0.1", "::1"}:
        raise UnsafeDsn("hostaddr no permitido")
    if params.get("service"):
        raise UnsafeDsn("service= no permitido")
    db = str(params.get("dbname") or "")
    if db not in ALLOWED_ADMIN_DBS:
        raise UnsafeDsn(f"base no permitida: {db}")
    return params


def _dsn_for(params: dict[str, str], dbname: str) -> str:
    p = dict(params, dbname=dbname)
    return " ".join(f"{k}={v}" for k, v in p.items())


@pytest.fixture()
def db():
    dsn = os.getenv("R3_TEST_DSN")
    try:
        params = check_safe_dsn(dsn)
    except UnsafeDsn as error:
        pytest.skip(f"BD de ensayo no habilitada: {error}")
    name = "r3t_" + uuid.uuid4().hex[:10]
    with psycopg.connect(_dsn_for(params, params["dbname"]), autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    conn = psycopg.connect(_dsn_for(params, name), autocommit=True)
    conn.execute("create extension if not exists citext")
    conn.execute("create extension if not exists pg_trgm")
    for f in ("supabase_stubs.sql", "schema_prod_tables.sql", "schema_prod_constraints.sql",
              "schema_prod_security.sql"):
        conn.execute((HERE / f).read_text())
    conn.execute((PREP / OPS_INFRA).read_text())
    try:
        yield conn
    finally:
        conn.close()
        with psycopg.connect(_dsn_for(params, params["dbname"]), autocommit=True) as admin:
            admin.execute(f'drop database "{name}" with (force)')
