import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from fastapi import HTTPException

from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services import case_user_actions as actions
from app.services.case_user_actions import ALLOWED_FIELDS, build_user_action_patch

NOW = datetime(2026, 10, 2, 22, 0, tzinfo=timezone.utc)
CASE_ID = "11111111-1111-1111-1111-111111111111"


class _Query:
    def __init__(self, db, op, payload=None):
        self.db, self.op, self.payload, self.filters = db, op, payload, {}

    def select(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        self.db.calls.append((self.op, dict(self.filters), self.payload))
        rows = [r for r in self.db.rows if all(str(r.get(k)) == str(v) for k, v in self.filters.items())]
        if self.op == "update":
            for row in rows:
                row.update(self.payload)
        return SimpleNamespace(data=[dict(r) for r in rows])


class _DB:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def table(self, name):
        assert name == "intelligent_cases", name
        return _Query(self, "select")


class BuildPatchTests(unittest.TestCase):
    def test_done_resolves_and_remembers_previous_status(self):
        patch = build_user_action_patch("done", {"status": "in_progress", "metadata": {"snoozed_until": "x", "keep": 1}}, now=NOW)
        self.assertEqual(patch["status"], "resolved")
        self.assertEqual(patch["resolved_at"], NOW.isoformat())
        self.assertEqual(patch["waiting_on"], "none")
        self.assertEqual(patch["metadata"], {"status_before_done": "in_progress", "keep": 1})
        self.assertLessEqual(set(patch), ALLOWED_FIELDS)

    def test_reopen_restores_previous_status(self):
        patch = build_user_action_patch("reopen", {"status": "resolved", "metadata": {"status_before_done": "new"}}, now=NOW)
        self.assertEqual(patch, {"status": "new", "resolved_at": None, "metadata": {}})

    def test_reopen_defaults_to_in_progress(self):
        patch = build_user_action_patch("reopen", {"status": "closed", "metadata": {"status_before_done": "archived"}}, now=NOW)
        self.assertEqual(patch["status"], "in_progress")

    def test_snooze_only_touches_metadata_never_due_at(self):
        until = NOW + timedelta(hours=3)
        patch = build_user_action_patch("snooze", {"status": "new", "due_at": "2026-10-03T00:00:00Z", "metadata": None}, now=NOW, until=until)
        self.assertEqual(set(patch), {"metadata"})
        self.assertEqual(patch["metadata"]["snoozed_until"], until.isoformat())

    def test_snooze_naive_datetime_is_utc(self):
        patch = build_user_action_patch("snooze", {"status": "new"}, now=NOW, until=datetime(2026, 10, 3, 9, 0))
        self.assertEqual(patch["metadata"]["snoozed_until"], "2026-10-03T09:00:00+00:00")

    def test_snooze_validation(self):
        for until in (None, NOW - timedelta(minutes=1), NOW + timedelta(days=91)):
            with self.assertRaises(HTTPException) as ctx:
                build_user_action_patch("snooze", {"status": "new"}, now=NOW, until=until)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_unsnooze(self):
        patch = build_user_action_patch("unsnooze", {"metadata": {"snoozed_until": "x"}}, now=NOW)
        self.assertEqual(patch, {"metadata": {}})

    def test_unknown_actions_rejected(self):
        for action in ("delete", "send", "archive", "update"):
            with self.assertRaises(HTTPException):
                build_user_action_patch(action, {"status": "new"}, now=NOW)


class ApplyUserActionTests(unittest.TestCase):
    def _run(self, db, account_id="acc-1", **kwargs):
        context = SimpleNamespace(user=SimpleNamespace(email="hector@example.com"))
        account = {"id": account_id, "workspace_id": "ws-1"}
        with mock.patch.object(actions, "require_google_account", return_value=(context, account)), \
                mock.patch.object(actions, "OAuthStorage", return_value=SimpleNamespace(client=db)), \
                mock.patch.object(actions, "create_case_event") as event:
            result = actions.apply_user_action(case_id=CASE_ID, **kwargs)
        return result, event

    def test_only_writes_the_users_own_case(self):
        db = _DB([{"id": CASE_ID, "account_id": "acc-1", "status": "new", "metadata": {}}])
        result, event = self._run(db, action="done")
        self.assertEqual(result["status"], "resolved")
        update = [c for c in db.calls if c[0] == "update"]
        self.assertEqual(len(update), 1)
        self.assertEqual(update[0][1], {"id": CASE_ID, "account_id": "acc-1"})
        self.assertLessEqual(set(update[0][2]), ALLOWED_FIELDS)
        self.assertEqual(event.call_args.kwargs["actor_type"], "user")
        self.assertEqual(event.call_args.kwargs["event_type"], "case_user_action")

    def test_other_users_case_is_404_and_untouched(self):
        db = _DB([{"id": CASE_ID, "account_id": "someone-else", "status": "new", "metadata": {}}])
        with self.assertRaises(HTTPException) as ctx:
            self._run(db, action="done")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertFalse([c for c in db.calls if c[0] == "update"])
        self.assertEqual(db.rows[0]["status"], "new")


class RouteGuardTests(unittest.TestCase):
    def test_user_action_route_requires_identity(self):
        request = SimpleNamespace(method="POST", url=SimpleNamespace(path=f"/cases/{CASE_ID}/user-action"))
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))

    def test_user_action_works_while_generic_patch_stays_locked(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api import cases as cases_api
        from app.security import mutation_guard

        app = FastAPI()
        app.include_router(cases_api.router)
        client = TestClient(app)
        detail = {
            "id": CASE_ID, "title": "t", "case_type": "general", "status": "resolved", "priority": "normal",
            "risk_score": 0, "confidence": 0.5, "waiting_on": "none", "opened_at": NOW.isoformat(),
            "last_activity_at": NOW.isoformat(), "source_count": 1, "reminder_count": 0,
            "workspace_id": "22222222-2222-2222-2222-222222222222", "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
        }
        with mock.patch.object(mutation_guard, "settings", SimpleNamespace(data_mutations_enabled=False)), \
                mock.patch.object(cases_api, "apply_user_action") as apply, \
                mock.patch.object(cases_api, "get_case", return_value=detail):
            locked = client.patch(f"/cases/{CASE_ID}", json={"status": "resolved"})
            self.assertEqual(locked.status_code, 423)
            ok = client.post(f"/cases/{CASE_ID}/user-action", json={"action": "done"})
            self.assertEqual(ok.status_code, 200, ok.text)
            apply.assert_called_once()
            self.assertEqual(apply.call_args.kwargs["action"], "done")
            bad = client.post(f"/cases/{CASE_ID}/user-action", json={"action": "delete"})
            self.assertEqual(bad.status_code, 422)
            not_uuid = client.post("/cases/not-a-uuid/user-action", json={"action": "done"})
            self.assertEqual(not_uuid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
