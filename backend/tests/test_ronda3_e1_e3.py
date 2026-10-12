"""Ronda 3 · E1 (sincronizador), E2 (duplicados), E3 (direction Gmail)."""
from __future__ import annotations

import logging
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")
from datetime import datetime, timedelta, timezone

import pytest

from tests.fake_supabase import FakeSupabase


# ---------------------------------------------------------------- E3
CASES = [
    (["SENT", "INBOX"], None, "outbound"),       # enviado a uno mismo
    (["SENT"], None, "outbound"),
    (["INBOX"], None, "inbound"),
    (["DRAFT"], None, "draft"),
    (["DRAFT", "SENT"], None, "draft"),
    (["CATEGORY_PROMOTIONS"], None, "inbound"),
    ([], "outbound", "outbound"),                  # sin etiquetas: respeta lo guardado (IMAP/Graph)
    (None, None, "inbound"),
]


@pytest.mark.parametrize("labels,stored,expected", CASES)
def test_e3_regla_unica_en_los_tres_modulos(labels, stored, expected):
    from app.services import case_engine, gmail_full_sync, safe_case_classifier
    from app.services.mail_direction import direction_from_labels

    assert direction_from_labels(labels, stored) == expected
    message = {"labels": labels, "direction": stored}
    assert case_engine._message_direction(message) == expected
    assert safe_case_classifier._message_direction(message) == expected
    if stored is None:
        assert gmail_full_sync._message_direction(labels or []) == expected


def test_e3_auto_enviado_sigue_clasificandose_como_entrante_en_triage():
    from app.services.mail_direction import is_self_delivered
    from app.services.safe_case_classifier import classify_message

    assert is_self_delivered(["SENT", "INBOX"]) and not is_self_delivered(["SENT"])
    sent_only = classify_message({"labels": ["SENT"], "subject": "x", "sender": "yo@example.test"},
                                 existing_case=None)
    assert sent_only[2] == "Mensaje enviado sin un caso abierto previo."
    self_sent = classify_message({"labels": ["SENT", "INBOX"], "subject": "x", "sender": "yo@example.test"},
                                 existing_case=None)
    assert self_sent[2] != "Mensaje enviado sin un caso abierto previo."


def test_e3_un_solo_lugar_define_la_regla():
    import pathlib
    root = pathlib.Path(__file__).parents[1] / "app"
    offenders = [str(p) for p in root.rglob("*.py")
                 if '"SENT" in' in p.read_text() and p.name != "mail_direction.py"]
    assert not offenders, offenders


# ---------------------------------------------------------------- E2
def _storage(fake):
    from app.services.oauth_storage import OAuthStorage

    storage = OAuthStorage.__new__(OAuthStorage)
    storage.client = fake
    return storage


def _world():
    return FakeSupabase({
        "workspace_members": [
            {"workspace_id": "ws-live", "profile_id": "p1", "status": "active"},
            {"workspace_id": "ws-other", "profile_id": "p2", "status": "active"},
            {"workspace_id": "ws-dead-2", "profile_id": "p3", "status": "active", "deleted_at": "2026-08-01"},
        ],
        "communication_accounts": [
            {"id": "orph-1", "workspace_id": "ws-dead-1", "provider": "google", "provider_account_id": "G", "status": "active"},
            {"id": "orph-2", "workspace_id": "ws-dead-2", "provider": "google", "provider_account_id": "G", "status": "active"},
            {"id": "other", "workspace_id": "ws-other", "provider": "google", "provider_account_id": "G", "status": "active"},
            {"id": "x", "workspace_id": "ws-dead-3", "provider": "google", "provider_account_id": "OTRO", "status": "active"},
        ],
    })


def test_e2_reconectar_crea_y_retira_huerfanas_sin_tocar_otros_usuarios():
    fake = _world()
    created = _storage(fake).upsert_communication_account(
        provider="google", provider_account_id="G", email="a@example.test", workspace_id="ws-live")
    st = {r["id"]: r["status"] for r in fake.tables["communication_accounts"]}
    assert st["orph-1"] == st["orph-2"] == "superseded"
    assert st["other"] == "active"          # otro usuario con el mismo buzón: intocable
    assert st["x"] == "active"              # otro buzón
    assert st[created["id"]] == "active"
    # no borra nada
    assert not [c for c in fake.calls if c[1] == "delete"]


def test_e2_reconectar_mismo_workspace_reutiliza_fila():
    fake = _world()
    fake.tables["communication_accounts"].append(
        {"id": "live", "workspace_id": "ws-live", "provider": "google", "provider_account_id": "G", "status": "needs_reauth"})
    acc = _storage(fake).upsert_communication_account(
        provider="google", provider_account_id="G", workspace_id="ws-live")
    assert acc["id"] == "live" and acc["status"] == "active"
    assert len([r for r in fake.tables["communication_accounts"] if r["workspace_id"] == "ws-live"]) == 1


def test_e2_fallo_al_retirar_no_rompe_conexion(caplog):
    fake = _world()
    storage = _storage(fake)
    storage._workspace_has_active_members = lambda _ws: (_ for _ in ()).throw(RuntimeError("boom a@b.c"))
    with caplog.at_level(logging.WARNING):
        acc = storage.upsert_communication_account(provider="google", provider_account_id="G", workspace_id="ws-live")
    assert acc["status"] == "active"
    assert "a@b.c" not in caplog.text and "RuntimeError" in caplog.text


def test_e2_borrado_de_usuario_desactiva_antes_de_borrar():
    from app.api import admin_ops

    fake = FakeSupabase({
        "workspace_members": [{"workspace_id": "ws1", "profile_id": "u1", "status": "active"}],
        "communication_accounts": [{"id": "a1", "workspace_id": "ws1", "status": "active"}],
    })
    admin_ops.cleanup_user_records(fake, "u1")
    ops = [(t, op) for t, op, _ in fake.calls]
    assert ops.index(("communication_accounts", "update")) < ops.index(("communication_accounts", "delete"))


# ---------------------------------------------------------------- E1
def test_e1_scheduler_apagado_por_defecto(monkeypatch):
    from app.services import automatic_mail_scheduler as s

    monkeypatch.delenv("HMS_AUTO_SYNC_ENABLED", raising=False)
    assert s._enabled() is False
    assert s.start_automatic_mail_scheduler() is False


def test_e1_solo_cuentas_activas_en_workspaces_con_miembros():
    from app.services.automatic_mail_scheduler import eligible_accounts

    fake = _world()
    fake.tables["communication_accounts"] += [
        {"id": "live", "workspace_id": "ws-live", "provider": "google", "status": "active"},
        {"id": "reauth", "workspace_id": "ws-live", "provider": "google", "status": "needs_reauth"},
        {"id": "sup", "workspace_id": "ws-live", "provider": "google", "status": "superseded"},
    ]
    ids = {a["id"] for a in eligible_accounts(fake)}
    assert ids == {"live", "other"}


def _job(status, mode, hours_ago):
    beat = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {"id": f"{status}-{mode}-{hours_ago}", "account_id": "a", "status": status, "mode": mode,
            "heartbeat_at": beat, "metadata": {}}


def test_e1_incremental_interrumpido_caducado_se_libera():
    from app.services.automatic_mail_scheduler import _active_job

    fake = FakeSupabase({"gmail_sync_jobs": [_job("interrupted", "incremental", 3)]})
    assert _active_job(fake, "a") is False
    job = fake.tables["gmail_sync_jobs"][0]
    assert job["status"] == "cancelled" and "stale_recovered_at" in job["metadata"]


def test_e1_interrumpido_reciente_o_historico_bloquea():
    from app.services.automatic_mail_scheduler import _active_job

    assert _active_job(FakeSupabase({"gmail_sync_jobs": [_job("interrupted", "incremental", 0.5)]}), "a") is True
    fake = FakeSupabase({"gmail_sync_jobs": [_job("interrupted", "historical", 50)]})
    assert _active_job(fake, "a") is True
    assert fake.tables["gmail_sync_jobs"][0]["status"] == "interrupted"   # nunca se reanuda solo
    assert _active_job(FakeSupabase({"gmail_sync_jobs": [_job("running", "incremental", 0)]}), "a") is True


def test_e1_invalid_grant_marca_needs_reauth_y_log_sin_pii(monkeypatch, caplog):
    from app.services import automatic_mail_scheduler as s

    fake = FakeSupabase({
        "workspace_members": [{"workspace_id": "ws", "profile_id": "p", "status": "active"}],
        "communication_accounts": [{"id": "acc-12345678-x", "workspace_id": "ws", "provider": "google", "status": "active",
                                    "email": "privado@example.test"}],
        "gmail_sync_jobs": [{"id": "j", "account_id": "acc-12345678-x", "mode": "historical", "status": "completed",
                             "metadata": {"guided_import": True}}],
    })

    class _Storage:
        client = fake
        def get_account(self, _):
            return None

    monkeypatch.setattr(s, "OAuthStorage", _Storage)
    monkeypatch.setattr(s, "_recover_recent_unprocessed", lambda **_: None)

    import app.api.auth as auth

    def boom(*_a, **_k):
        raise RuntimeError("('invalid_grant: Token has been expired or revoked.', privado@example.test)")

    monkeypatch.setattr(auth, "get_google_credentials_for_account", boom)
    started = []
    monkeypatch.setattr(s, "start_guided_import", lambda **k: started.append(k))
    with caplog.at_level(logging.INFO):
        s._cycle()
    assert fake.tables["communication_accounts"][0]["status"] == "needs_reauth"
    assert not started
    assert "privado@example.test" not in caplog.text and "needs_reauth" in caplog.text
    # siguiente ciclo: ya no se reintenta
    s._cycle()
    assert len([c for c in fake.calls if c[0] == "communication_accounts" and c[1] == "update"]) == 1


def test_e1_reconexion_reactiva_cuenta_needs_reauth():
    fake = FakeSupabase({"workspace_members": [], "communication_accounts": [
        {"id": "a", "workspace_id": "ws", "provider": "google", "provider_account_id": "G", "status": "needs_reauth"}]})
    acc = _storage(fake).upsert_communication_account(provider="google", provider_account_id="G", workspace_id="ws")
    assert acc["status"] == "active"
