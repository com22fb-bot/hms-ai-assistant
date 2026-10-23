"""Cuentas protegidas: todo el historial sin filtro de fecha; normales 90 días; anual 183."""
import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from app.services import account_lifecycle as lc
from app.services import gmail_import_inventory as gi
from app.services import microsoft_import as mi
from app.services import yahoo_import as yi

NOW = datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)


class _Q:
    def __init__(self, rows):
        self.rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def execute(self): return type("R", (), {"data": self.rows})()


class _Client:
    def __init__(self, email, plans=()):
        self.email, self.plans = email, list(plans)
    def table(self, name):
        if name == "workspace_members": return _Q([{"profile_id": "p1"}])
        if name == "profiles": return _Q([{"id": "p1", "email": self.email}])
        if name == "account_plans": return _Q(self.plans)
        return _Q([])


class ProtectedWindowTests(unittest.TestCase):
    def test_protected_emails_include_env(self):
        with mock.patch.dict(os.environ, {"ACCOUNT_CLEANUP_PROTECTED_EMAILS": "hsalcidor@yahoo.com", "ADMIN_EMAILS": ""}):
            self.assertIn("hsalcidor@yahoo.com", lc.protected_emails())
            self.assertIn("hmcelinfo@gmail.com", lc.protected_emails())

    def test_workspace_windows(self):
        with mock.patch.dict(os.environ, {"ACCOUNT_CLEANUP_PROTECTED_EMAILS": "hsalcidor@yahoo.com", "ADMIN_EMAILS": ""}):
            self.assertEqual(lc.history_days_for_workspace(_Client("hmcelinfo@gmail.com"), "w"), -1)
            self.assertEqual(lc.history_days_for_workspace(_Client("HSalcidor@yahoo.com"), "w"), -1)
            self.assertEqual(lc.history_days_for_workspace(_Client("otro@x.com"), "w"), 90)
            annual = [{"plan_code": "annual", "status": "active"}]
            self.assertEqual(lc.history_days_for_workspace(_Client("otro@x.com", annual), "w"), 183)
            self.assertEqual(lc.plan_status_for_workspace(_Client("hmcelinfo@gmail.com"), "w")["history_days"], -1)

    def test_history_start(self):
        self.assertEqual(gi.history_start(NOW, -1), gi.HISTORY_EPOCH)
        self.assertEqual((NOW - gi.history_start(NOW, 90)).days, 90)
        self.assertEqual((NOW - gi.history_start(NOW, 183)).days, 183)
        self.assertEqual(yi._history_window(NOW, -1)[0], gi.HISTORY_EPOCH)
        self.assertEqual(mi._history_window(NOW, -1)[0], gi.HISTORY_EPOCH)
        self.assertEqual((NOW - yi._history_window(NOW, 90)[0]).days, 90)

    def test_gmail_query_has_no_after_when_unlimited(self):
        with mock.patch.object(gi, "_service", return_value=None), \
             mock.patch.object(gi, "_list_message_ids", return_value=["a", "b"]) as lst:
            snap = gi.initial_import_snapshot(None, cutoff_at=NOW, history_days=-1)
            self.assertNotIn("after:", lst.call_args.kwargs["query"])
            self.assertEqual(snap["history_days"], -1)
            gi.initial_import_snapshot(None, cutoff_at=NOW, history_days=90)
            self.assertIn("after:", lst.call_args.kwargs["query"])

    def test_imap_search_all_when_unlimited(self):
        client = mock.Mock()
        client.uid.return_value = ("OK", [b"1 2"])
        with mock.patch.object(yi, "_select_folder"):
            self.assertEqual(yi._folder_uids_since(client, "INBOX", gi.HISTORY_EPOCH), ["1", "2"])
            self.assertEqual(client.uid.call_args.args, ("SEARCH", None, "ALL"))
            yi._folder_uids_since(client, "INBOX", gi.history_start(NOW, 90))
            self.assertEqual(client.uid.call_args.args[2], "SINCE")


if __name__ == "__main__":
    unittest.main()
