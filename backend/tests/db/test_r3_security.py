"""RLS, grants, SECURITY DEFINER y creación de workspace con la seguridad real
extraída del catálogo de producción (solo lectura) sobre stubs de auth.
NO es Supabase real: PostgREST, auth.users con su trigger y roles reales
siguen pendientes de una rama de Supabase."""
from __future__ import annotations

import pytest

from tests.db.conftest import PREP
from tests.db.test_r3_consolidation import World, one, run


def as_user(conn, profile_id):
    conn.execute("set role authenticated")
    conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (profile_id,))


def reset(conn):
    conn.execute("reset role")


def test_rls_aisla_buzones_por_miembro(db):
    w = World(db)
    run(db, "003_orphan_guards.sql")
    as_user(db, w.p)
    try:
        visible = {r[0] for r in db.execute("select id::text from communication_accounts").fetchall()}
        # ve solo buzones de sus workspaces; nunca huérfanas ni de otro usuario
        assert w.live in visible and w.two_live[0] in visible
        assert not visible & {*w.orphans, *w.nocanon, w.two_live[1], w.two_live[2], w.other}
        # tablas sin política: nada visible para authenticated (la API usa service role)
        assert one(db, "select count(*) from communication_messages") == 0
    finally:
        reset(db)
    as_user(db, w.p)
    try:
        with pytest.raises(Exception):           # sin GRANT: ni siquiera se puede consultar
            db.execute("select count(*) from oauth_credentials")
    finally:
        reset(db)


def test_ops_y_funciones_r3_no_accesibles(db):
    w = World(db)
    run(db, "002a_merge_map.sql")
    run(db, "003_orphan_guards.sql")
    for sql in ("select * from ops_r3_merge_map", "select * from ops_r3_rows",
                "select public.hms_r3_deactivate_orphan_accounts()",
                "select * from ops_r3_rollback(gen_random_uuid())",
                "select public.hms_ensure_personal_workspace(gen_random_uuid())"):
        as_user(db, w.p)
        try:
            with pytest.raises(Exception):
                db.execute(sql)
        finally:
            reset(db)


def test_trigger_security_definer_y_search_path(db):
    run(db, "003_orphan_guards.sql")
    secdef, cfg = db.execute("select prosecdef, proconfig from pg_proc "
                             "where proname='hms_r3_deactivate_orphan_accounts'").fetchone()
    assert secdef is True and cfg == ["search_path=public, pg_temp"]


def test_trigger_desactiva_al_quedar_sin_miembros(db):
    w = World(db)
    run(db, "003_orphan_guards.sql")
    # baja lógica (deleted_at)
    db.execute("update workspace_members set deleted_at=now() where workspace_id=%s", (w.ws_live,))
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "inactive"


def test_trigger_no_toca_workspace_con_otro_miembro_activo(db):
    w = World(db)
    run(db, "003_orphan_guards.sql")
    db.execute("insert into workspace_members (workspace_id, profile_id, status) values (%s,%s,'active')",
               (w.ws_live, w.p2))
    db.execute("delete from workspace_members where workspace_id=%s and profile_id=%s", (w.ws_live, w.p))
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "active"


def test_invitado_no_cuenta_como_miembro_activo(db):
    # no existe tabla de invitaciones en prod; una membresía 'invited' no mantiene vivo el buzón
    w = World(db)
    run(db, "003_orphan_guards.sql")
    db.execute("insert into workspace_members (workspace_id, profile_id, status) values (%s,%s,'invited')",
               (w.ws_live, w.p2))
    db.execute("delete from workspace_members where workspace_id=%s and profile_id=%s", (w.ws_live, w.p))
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "inactive"


def test_authenticated_no_puede_borrar_membresias(db):
    w = World(db)
    run(db, "003_orphan_guards.sql")
    as_user(db, w.p)
    try:
        db.execute("delete from workspace_members where workspace_id=%s", (w.ws_live,))
    finally:
        reset(db)
    assert one(db, "select count(*) from workspace_members where workspace_id=%s", w.ws_live) == 1
    assert one(db, "select status from communication_accounts where id=%s", w.live) == "active"


def test_crear_workspace_personal_y_trigger(db):
    run(db, "003_orphan_guards.sql")
    db.execute("insert into profiles (id, email, full_name) values "
               "('11111111-1111-1111-1111-111111111111', 'n@example.test', 'Nuevo')")
    ws1 = one(db, "select public.hms_ensure_personal_workspace('11111111-1111-1111-1111-111111111111')")
    ws2 = one(db, "select public.hms_ensure_personal_workspace('11111111-1111-1111-1111-111111111111')")
    assert ws1 == ws2
    assert one(db, "select role||'/'||status from workspace_members where workspace_id=%s", ws1) == "owner/active"
    db.execute("insert into communication_accounts (workspace_id, provider, provider_account_id, status) "
               "values (%s,'google','N','active')", (ws1,))
    # reactivar membresía (on conflict) no desactiva nada
    one(db, "select public.hms_ensure_personal_workspace('11111111-1111-1111-1111-111111111111')")
    assert one(db, "select status from communication_accounts where workspace_id=%s", ws1) == "active"
