import logging
from types import SimpleNamespace

import app.services.guided_import_job_service as svc


def test_push_suppressed_by_default(monkeypatch, caplog):
    calls = []
    monkeypatch.setattr(svc, "settings", SimpleNamespace(import_push_notifications_enabled=False))
    monkeypatch.setattr(svc, "notify_actionable_messages", lambda **kw: calls.append(kw))
    with caplog.at_level(logging.INFO, logger=svc.__name__):
        svc._notify_or_suppress(account_id="a", workspace_id="w", candidates=7)
    assert calls == []
    assert "candidates=7" in caplog.text


def test_push_sent_when_enabled(monkeypatch):
    calls = []
    monkeypatch.setattr(svc, "settings", SimpleNamespace(import_push_notifications_enabled=True))
    monkeypatch.setattr(svc, "notify_actionable_messages", lambda **kw: calls.append(kw))
    svc._notify_or_suppress(account_id="a", workspace_id="w", candidates=0)
    assert calls == [{"account_id": "a", "workspace_id": "w", "limit": 1}]


def test_config_default_false(monkeypatch):
    from app.core.config import Settings
    monkeypatch.delenv("IMPORT_PUSH_NOTIFICATIONS_ENABLED", raising=False)
    assert Settings().import_push_notifications_enabled is False
    monkeypatch.setenv("IMPORT_PUSH_NOTIFICATIONS_ENABLED", "true")
    assert Settings().import_push_notifications_enabled is True


def test_no_direct_notify_call_in_job_loop():
    import inspect
    src = inspect.getsource(svc)
    assert src.count("notify_actionable_messages(") == 1  # solo dentro del helper
