"""Cancelación real, pipeline descarga/identificación y UID FETCH por lote."""
import threading
import time

from app.services import guided_import_job_service as g
from app.services import yahoo_import as y


class Store:
    def __init__(self, job):
        self.job = dict(job)
        self.lock = threading.Lock()

    def get(self, _id):
        with self.lock:
            return dict(self.job)

    def update(self, _id, values):
        with self.lock:
            self.job.update(values)
            return dict(self.job)


def _wire(monkeypatch, store, pages, on_page=None, classify_delay=0.0):
    calls = {"pages": 0, "classified": 0, "push": 0}
    monkeypatch.setattr(g, "_job", store.get)
    monkeypatch.setattr(g, "_update_job", store.update)

    class _Chain:
        def __getattr__(self, _):
            return lambda *a, **k: self

    class S:
        client = _Chain()

        def get_account(self, _):
            return {"id": "a", "workspace_id": "w", "provider": "yahoo", "email": "x@yahoo.com"}

    monkeypatch.setattr(g, "_storage", lambda: S())
    monkeypatch.setattr(g, "is_icloud_provider", lambda a: False)
    monkeypatch.setattr(g, "is_yahoo_provider", lambda a: True)
    monkeypatch.setattr(g, "_yahoo_secret", lambda a: ("x", "p", False))

    def page(**kw):
        calls["pages"] += 1
        if on_page:
            on_page(calls["pages"])
        off = kw["offset"]
        n = min(kw["batch_size"], len(kw["refs"]) - off)
        more = off + n < len(kw["refs"])
        return {"page_found": n, "inserted": n, "inserted_message_ids": [f"m{off+i}" for i in range(n)],
                "next_page_token": str(off + n) if more else None, "has_more": more, "timing": {}}

    monkeypatch.setattr(g, "sync_yahoo_page", page)
    monkeypatch.setattr(g, "apply_active_rules_to_unprocessed_messages", lambda **k: None)
    monkeypatch.setattr(g, "match_watch_rules_for_account", lambda **k: None)

    def classify(**k):
        time.sleep(classify_delay)
        calls["classified"] += len(k["message_ids"])
        return {"processed": len(k["message_ids"]), "created_cases": 1}

    monkeypatch.setattr(g, "classify_pending_messages", classify)
    monkeypatch.setattr(g, "notify_actionable_messages", lambda **k: calls.__setitem__("push", calls["push"] + 1))
    return calls


def _job(n):
    return {"id": "job-1", "account_id": "a", "workspace_id": "w", "status": "queued", "batch_size": 10,
            "next_page_token": "0", "metadata": {"guided_import": True, "yahoo_refs": [f"r{i}" for i in range(n)]}}


def test_completes_and_classifies_everything_without_push(monkeypatch):
    store = Store(_job(35))
    calls = _wire(monkeypatch, store, pages=4)
    g._run_job("job-1")
    assert store.job["status"] == "completed"
    assert store.job["messages_inserted"] == 35
    assert store.job["cases_processed"] == 35 == calls["classified"]
    assert calls["push"] == 0  # IMPORT_PUSH_NOTIFICATIONS_ENABLED=false por defecto


def test_cancel_requested_stops_loop_cleanly(monkeypatch):
    store = Store(_job(1000))

    def on_page(n):
        if n == 2:
            store.update("job-1", {"cancel_requested": True})

    calls = _wire(monkeypatch, store, pages=100, on_page=on_page)
    g._run_job("job-1")
    assert store.job["status"] == "cancelled"
    assert calls["pages"] == 2  # no hay tercera página tras cancelar
    assert store.job["messages_inserted"] == 20


def test_status_cancelled_is_not_overwritten_to_running(monkeypatch):
    store = Store(_job(1000))

    def on_page(n):
        if n == 1:
            store.update("job-1", {"status": "cancelled"})

    calls = _wire(monkeypatch, store, pages=100, on_page=on_page)
    g._run_job("job-1")
    assert store.job["status"] == "cancelled"
    assert calls["pages"] == 1


def test_cancelled_job_is_not_resumed(monkeypatch):
    started = []
    monkeypatch.setattr(g, "_start_thread", lambda job_id: started.append(job_id))
    g._resume_if_needed({"id": "j", "status": "running", "cancel_requested": True})
    g._resume_if_needed({"id": "j", "status": "cancelled"})
    assert started == []
    g._resume_if_needed({"id": "j", "status": "interrupted"})
    assert started == ["j"]


def test_download_does_not_wait_for_identification(monkeypatch):
    """Pipeline: con identificación lenta, la descarga termina sus páginas antes."""
    store = Store(_job(100))
    calls = _wire(monkeypatch, store, pages=10, classify_delay=0.05)
    t0 = time.monotonic()
    g._run_job("job-1")
    assert store.job["status"] == "completed"
    assert calls["classified"] == 100
    assert time.monotonic() - t0 < 0.05 * 10 + 0.4


class FakeImap:
    def __init__(self):
        self.commands = []

    def uid(self, cmd, ids, spec):
        self.commands.append((cmd, ids, spec))
        out = []
        for uid in ids.split(","):
            raw = f"Subject: s{uid}\r\nFrom: a@b.c\r\n\r\nbody".encode()
            out.append((f"1 (UID {uid} FLAGS (\\Seen) BODY[] {{{len(raw)}}}".encode(), raw))
            out.append(b")")
        return "OK", out


def test_uid_fetch_batch_is_one_command_and_peek_only():
    imap = FakeImap()
    got = y._fetch_uid_batch(imap, ["11", "12", "13"])
    assert sorted(got) == ["11", "12", "13"]
    assert len(imap.commands) == 1
    cmd, ids, spec = imap.commands[0]
    assert cmd == "FETCH" and ids == "11,12,13"
    assert "BODY.PEEK[]" in spec and "STORE" not in spec.upper()
    assert "\\Seen" in got["12"][1]


def test_continue_does_not_redownload_existing_messages(monkeypatch):
    """OBS-CANC-01: un job nuevo sobre lo ya guardado no vuelve a pedir cuerpos a IMAP."""
    from unittest import mock

    refs = [f"Inbox\x1f{100 + i}" for i in range(5)]
    imap = FakeImap()

    class Q:
        def __getattr__(self, _):
            return lambda *a, **k: self

        def execute(self):
            return type("R", (), {"data": []})()

    class St:
        client = type("C", (), {"table": lambda self, n: Q()})()

    existing = {f"yahoo:Inbox:{100 + i}" for i in range(5)}
    with mock.patch.object(y, "OAuthStorage", St), \
         mock.patch.object(y, "_open_mailbox_client", lambda *a, **k: imap), \
         mock.patch.object(y, "_existing_message_ids", lambda **k: existing), \
         mock.patch.object(y, "_select_folder", lambda *a, **k: None), \
         mock.patch.object(y, "_prepare_imap_secret", lambda e, p, **k: (e, p)):
        out = y.sync_yahoo_page(account={"id": "a", "email": "x@yahoo.com"}, app_password="p", refs=refs, offset=0)
    assert out["inserted"] == 0 and out["duplicates"] == 5
    assert imap.commands == []  # sin FETCH: no se descarga de nuevo


def test_final_sweep_identifies_pending_once(monkeypatch):
    """Al completar, un solo barrido sin message_ids toma lo que quedó con case_processed=false."""
    store = Store(_job(10))
    _wire(monkeypatch, store, pages=1)
    sweeps = []

    def classify(**k):
        if "message_ids" not in k:
            sweeps.append(k)
            return {"processed": 50, "created_cases": 0}
        return {"processed": len(k["message_ids"]), "created_cases": 0}

    monkeypatch.setattr(g, "classify_pending_messages", classify)
    g._run_job("job-1")
    assert store.job["status"] == "completed"
    assert len(sweeps) == 1 and sweeps[0]["limit"] == 1000
    assert store.job["cases_processed"] == 10 + 50
