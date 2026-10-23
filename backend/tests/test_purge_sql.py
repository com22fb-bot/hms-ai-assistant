"""Pruebas de admin_purge_user v2 contra un Postgres real y efímero (nunca producción).

Arranca un clúster temporal con initdb (los runners de GitHub traen PostgreSQL) y aplica
supabase/tests/purge_fixture.sql + la migración 20261023_002 + purge_seed.sql.
"""
import glob
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "supabase"
U, O, A, D = (f"00000000-0000-0000-0000-0000000000{x}" for x in ("aa", "bb", "cc", "dd"))
ACC1, ACC2, ACC3, ACC4 = (f"20000000-0000-0000-0000-00000000000{i}" for i in (1, 2, 3, 4))


def _bin(name):
    found = shutil.which(name)
    if found:
        return found
    cands = sorted(glob.glob(f"/usr/lib/postgresql/*/bin/{name}"))
    return cands[-1] if cands else None


@pytest.fixture(scope="module")
def pg():
    initdb, pg_ctl, psql = _bin("initdb"), _bin("pg_ctl"), _bin("psql")
    if not (initdb and pg_ctl and psql):
        if os.getenv("PURGE_SQL_REQUIRED"):
            pytest.fail("PostgreSQL requerido en este job y no está disponible")
        pytest.skip("PostgreSQL no disponible")
    tmp = tempfile.mkdtemp(prefix="purge-pg-")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    subprocess.run([initdb, "-D", f"{tmp}/d", "-U", "postgres", "-A", "trust"], check=True, capture_output=True)
    subprocess.run([pg_ctl, "-D", f"{tmp}/d", "-o", f"-p {port} -k {tmp} -c listen_addresses=''", "-l", f"{tmp}/log", "-w", "start"],
                   check=True, capture_output=True)
    base = [psql, "-h", tmp, "-p", str(port), "-U", "postgres", "-v", "ON_ERROR_STOP=1", "-q", "-tA"]

    def make_db(name):
        subprocess.run(base + ["-d", "postgres", "-c", f"create database {name}"], check=True, capture_output=True)
        for f in ("tests/purge_fixture.sql", "migrations/20261023_002_admin_purge_user_v2.sql", "tests/purge_seed.sql"):
            subprocess.run(base + ["-d", name, "-f", str(ROOT / f)], check=True, capture_output=True)

        def q(sql, ok=True):
            r = subprocess.run(base + ["-d", name, "-c", sql], capture_output=True, text=True)
            if ok and r.returncode:
                raise AssertionError(r.stderr)
            return r.stdout.strip() if ok else r
        return q
    counter = iter(range(1000))
    yield lambda: make_db(f"t{next(counter)}")
    subprocess.run([pg_ctl, "-D", f"{tmp}/d", "-m", "immediate", "stop"], capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)


SNAPSHOT = """select json_build_object(
 'acc',(select json_agg(row_to_json(a) order by id) from (select id,status,connected_by_profile_id from communication_accounts) a),
 'msgs',(select count(*) from communication_messages),'att',(select count(*) from attachments),
 'cred',(select count(*) from oauth_credentials),'prof',(select count(*) from profiles),'auth',(select count(*) from auth.users),
 'ws',(select json_agg(row_to_json(w) order by id) from (select id,owner_profile_id from workspaces) w),
 'bk',(select count(*) from hms_backup_test_20260804.communication_messages),'otro',(select count(*) from otro_esquema.communication_messages),
 'bx',(select count(*) from hms_backupx.profiles),'queue',(select count(*) from admin_storage_purge_queue),
 'events',(select count(*) from admin_events))"""


def test_dry_run_devuelve_plan_y_no_cambia_nada(pg):
    q = pg()
    before = q(SNAPSHOT)
    plan = json.loads(q(f"select admin_purge_user('{U}', true)"))
    assert q(SNAPSHOT) == before
    assert plan["dry_run"] is True and "storage_paths" not in plan
    assert plan["workspaces_deleted"] == 1 and plan["shared_kept"] == 2 and plan["storage_queued"] == 5
    assert plan["counts"]["communication_messages"] == 5
    assert plan["backup_counts"] == {"hms_backup_test_20260804.communication_accounts": 1,
                                     "hms_backup_test_20260804.communication_messages": 5}
    print("\nDRY-RUN:", json.dumps(plan, indent=1, sort_keys=True))


def test_real_coincide_con_dry_run(pg):
    q = pg()
    plan = json.loads(q(f"select admin_purge_user('{U}', true)"))
    real = json.loads(q(f"select admin_purge_user('{U}', false)"))
    for k in ("counts", "backup_counts", "rows_total", "shared_kept", "storage_queued", "workspaces_deleted"):
        assert real[k] == plan[k], k


def test_espacio_compartido_conserva_buzones_y_mensajes(pg):
    q = pg()
    q(f"select admin_purge_user('{U}')")
    # Buzón de U en W2 (dueño O): se conserva, se desconecta, pasa a O y pierde credenciales de U.
    assert q(f"select status||','||connected_by_profile_id from communication_accounts where id='{ACC2}'") == f"disconnected,{O}"
    assert q(f"select count(*) from communication_messages where account_id='{ACC2}'") == "5"
    assert q(f"select count(*) from attachments a join communication_messages m on m.id=a.message_id where m.account_id='{ACC2}'") == "5"
    assert q(f"select count(*) from oauth_credentials where account_id='{ACC2}'") == "0"
    # Buzón de O en W2: intacto (incluida su credencial y su aviso).
    assert q(f"select status||','||connected_by_profile_id from communication_accounts where id='{ACC3}'") == f"active,{O}"
    assert q(f"select count(*) from oauth_credentials where account_id='{ACC3}'") == "1"
    assert q(f"select count(*) from hms_notifications where profile_id='{O}'") == "1"
    # W3 (dueño U, con D): se conserva y pasa a D, junto con el buzón.
    assert q("select owner_profile_id from workspaces where name='W3'") == D
    assert q(f"select connected_by_profile_id from communication_accounts where id='{ACC4}'") == D
    assert q(f"select count(*) from communication_messages where account_id='{ACC4}'") == "5"
    # W1 (solo U; el otro miembro estaba 'removed'): borrado completo.
    assert q("select count(*) from workspaces where name='W1'") == "0"
    assert q(f"select count(*) from communication_messages where account_id='{ACC1}'") == "0"
    assert q(f"select count(*) from auth.users where id='{U}'") == "0"
    assert q(f"select count(*) from auth.identities where user_id='{U}'") == "0"


def test_integridad_sin_huerfanos(pg):
    q = pg()
    q(f"select admin_purge_user('{U}')")
    assert q("""select count(*) from communication_messages m left join communication_accounts a on a.id=m.account_id where a.id is null""") == "0"
    assert q("""select count(*) from communication_accounts where connected_by_profile_id is null""") == "0"
    assert q("""select count(*) from workspaces where owner_profile_id is null""") == "0"
    assert q("""select count(*) from attachments x left join communication_messages m on m.id=x.message_id where m.id is null""") == "0"


def test_respaldos_solo_por_patron_y_solo_filas_del_usuario(pg):
    q = pg()
    q(f"select admin_purge_user('{U}')")
    assert q("select count(*) from hms_backup_test_20260804.communication_messages") == "1"  # queda la de O
    assert q("select count(*) from hms_backup_test_20260804.communication_accounts") == "1"
    assert q("select count(*) from otro_esquema.communication_messages") == "1"           # fuera del patrón
    assert q("select count(*) from hms_backupx.profiles") == "1"                           # fuera del patrón
    assert q("select count(*) from information_schema.schemata where schema_name like 'hms_backup%'") == "2"


def test_no_borra_admin_y_es_idempotente(pg):
    q = pg()
    r = q(f"select admin_purge_user('{A}')", ok=False)
    assert r.returncode and "no se borra a un administrador" in r.stderr
    q(f"select admin_purge_user('{U}')")
    again = json.loads(q(f"select admin_purge_user('{U}')"))
    assert again["counts"]["auth_users"] == 0 and again["storage_queued"] == 0


def test_cola_storage_duradera_reintentos_y_fallido(pg):
    q = pg()
    q(f"select admin_purge_user('{U}')")
    assert q("select count(*) from admin_storage_purge_queue where status='pendiente'") == "5"
    assert q("select status from admin_events order by created_at desc limit 1") == "abierto"
    ids = q("select string_agg(id::text, ',') from admin_storage_purge_claim(2)")
    assert len(ids.split(",")) == 2
    # Fallo: vuelve a pendiente con espera; no se vuelve a reclamar enseguida.
    mark = json.loads(q(f"select admin_storage_purge_mark(array[{ids}]::bigint[], false, 'timeout')"))
    assert mark == {"hecho": 0, "fallido": 0, "pendiente": 2}
    others = q("select string_agg(id::text, ',') from admin_storage_purge_claim(10)")
    assert set(others.split(",")).isdisjoint(ids.split(",")) and len(others.split(",")) == 3
    # Al agotar intentos pasa a 'fallido' (visible, no se pierde).
    q(f"update admin_storage_purge_queue set attempts=max_attempts, next_attempt_at=now() where id in ({ids})")
    assert json.loads(q(f"select admin_storage_purge_mark(array[{ids}]::bigint[], false, 'x')"))["fallido"] == 2
    assert json.loads(q(f"select admin_storage_purge_mark(array[{others}]::bigint[], true)"))["hecho"] == 3
    st = json.loads(q("select admin_storage_purge_status()"))
    assert (st["pendiente"], st["fallido"], st["hecho"]) == (0, 2, 3)
