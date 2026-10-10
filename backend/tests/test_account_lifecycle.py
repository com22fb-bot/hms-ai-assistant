import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import account_lifecycle as lc


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], "select", None

    def select(self, *_a, **_k): return self
    def eq(self, c, v): self.filters.append((c, [v])); return self
    def in_(self, c, v): self.filters.append((c, list(v))); return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a): return self
    def update(self, payload): self.op, self.payload = "update", payload; return self
    def insert(self, payload): self.op, self.payload = "insert", payload; return self

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        match = [r for r in rows if all(str(r.get(c)) in [str(x) for x in v] for c, v in self.filters)]
        if self.op == "update":
            for r in match:
                r.update(self.payload)
        if self.op == "insert":
            rows.append(dict(self.payload))
        return type("R", (), {"data": match})()


class _Client:
    def __init__(self, db): self.db = db
    def table(self, name): return _Q(self.db, name)


NOW = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)


def _db():
    return {
        "profiles": [
            {"id": "u1", "email": "trial-old@example.com"},
            {"id": "u2", "email": "trial-mid@example.com"},
            {"id": "u3", "email": "lapsed@example.com"},
            {"id": "u4", "email": "hmcelinfo@gmail.com"},
            {"id": "u5", "email": "annual@example.com"},
        ],
        "account_plans": [
            {"user_id": "u1", "plan_code": "trial", "status": "trialing", "trial_ends_at": (NOW - timedelta(days=8)).isoformat()},
            {"user_id": "u2", "plan_code": "trial", "status": "trialing", "trial_ends_at": (NOW - timedelta(days=4)).isoformat()},
            {"user_id": "u3", "plan_code": "monthly", "status": "lapsed", "period_ends_at": (NOW - timedelta(days=29, hours=1)).isoformat()},
            {"user_id": "u4", "plan_code": "trial", "status": "trialing", "trial_ends_at": (NOW - timedelta(days=60)).isoformat()},
            {"user_id": "u5", "plan_code": "annual", "status": "active", "period_ends_at": (NOW + timedelta(days=200)).isoformat()},
        ],
        "workspace_members": [{"workspace_id": "w5", "profile_id": "u5"}, {"workspace_id": "w1", "profile_id": "u1"},
                              {"workspace_id": "w4", "profile_id": "u4"}],
    }


class HistoryWindowTests(unittest.TestCase):
    def test_plan_windows(self):
        self.assertEqual(lc.history_days_for_plan("monthly"), 90)
        self.assertEqual(lc.history_days_for_plan("trial"), 90)
        self.assertEqual(lc.history_days_for_plan(None), 90)
        self.assertEqual(lc.history_days_for_plan("annual"), 183)

    def test_workspace_windows(self):
        client = _Client(_db())
        self.assertEqual(lc.history_days_for_workspace(client, "w5"), 183)
        self.assertEqual(lc.history_days_for_workspace(client, "w1"), 90)
        self.assertEqual(lc.history_days_for_workspace(client, "w4"), 183)  # dueño protegido
        self.assertEqual(lc.history_days_for_workspace(client, "nope"), 90)


class ScheduleTests(unittest.TestCase):
    def test_next_cleanup_is_3am_mexico_city(self):
        # 9:00 UTC = 3:00 CDMX (UTC-6): ya pasó -> mañana 9:00 UTC
        nxt = lc.next_cleanup_at(NOW)
        self.assertEqual(nxt, datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(lc.next_cleanup_at(NOW - timedelta(hours=1)), NOW)


class CleanupTests(unittest.TestCase):
    def test_dry_run_counts_and_never_deletes(self):
        db = _db()
        deleted = []
        result = lc.run_daily_cleanup(_Client(db), now=NOW, delete=False, send_reminders=False,
                                      deleter=lambda c, u: deleted.append(u))
        self.assertTrue(result["dry_run"])
        self.assertEqual(deleted, [])
        self.assertEqual(result["would_delete"], 1)  # u1
        self.assertEqual(result["skipped_protected"], 1)  # hmcelinfo
        self.assertEqual(db["account_cleanup_runs"][0]["dry_run"], True)

    def test_delete_enabled_skips_protected(self):
        deleted = []
        result = lc.run_daily_cleanup(_Client(_db()), now=NOW, delete=True, send_reminders=False,
                                      deleter=lambda c, u: deleted.append(u))
        self.assertEqual(deleted, ["u1"])
        self.assertNotIn("u4", deleted)
        self.assertEqual(result["deleted"], 1)

    def test_scheduled_reminders_midpoint_and_final(self):
        db = _db()
        sent = []
        result = lc.run_daily_cleanup(_Client(db), now=NOW, delete=False, send_reminders=True,
                                      sender=lambda to, s, b: sent.append(to) or True, deleter=lambda c, u: None)
        # u2: 4 días tras fin de prueba (mitad = 3.5) -> recordatorio de mitad
        # u3: 29d1h tras vencimiento (borra a 30d) -> último recordatorio
        self.assertEqual(sorted(sent), ["lapsed@example.com", "trial-mid@example.com"])
        self.assertEqual(result["reminders_mid"], 1)
        self.assertEqual(result["reminders_final"], 1)
        again = lc.run_daily_cleanup(_Client(db), now=NOW, delete=False, send_reminders=True,
                                     sender=lambda to, s, b: sent.append(to) or True, deleter=lambda c, u: None)
        self.assertEqual(again["reminders_mid"] + again["reminders_final"], 0)

    def test_no_reminders_when_flag_off(self):
        sent = []
        lc.run_daily_cleanup(_Client(_db()), now=NOW, delete=False, send_reminders=False,
                             sender=lambda to, s, b: sent.append(to) or True)
        self.assertEqual(sent, [])


class OverviewTests(unittest.TestCase):
    def test_groups_and_days_left(self):
        ov = lc.lifecycle_overview(_Client(_db()), NOW)
        trials = {r["email"]: r for r in ov["trials"]}
        self.assertEqual(trials["trial-mid@example.com"]["days_left"], 3)
        self.assertTrue(trials["hmcelinfo@gmail.com"]["protected"])
        self.assertEqual([r["email"] for r in ov["lapsed"]], ["lapsed@example.com"])
        self.assertEqual(ov["lapsed"][0]["days_left"], 1)
        self.assertFalse(ov["deletion_enabled"])

    def test_manual_reminder_button_skips_protected(self):
        sent = []
        res = lc.send_subscribe_reminders(_Client(_db()), "trial", now=NOW,
                                          sender=lambda to, s, b: sent.append(to) or True)
        self.assertNotIn("hmcelinfo@gmail.com", sent)
        self.assertEqual(res["skipped_protected"], 1)
        self.assertEqual(res["sent"], 2)
        with self.assertRaises(ValueError):
            lc.send_subscribe_reminders(_Client(_db()), "otro", now=NOW, sender=lambda *a: True)


if __name__ == "__main__":
    unittest.main()
