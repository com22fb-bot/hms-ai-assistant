import json
from datetime import datetime, timedelta, timezone

from app.services import account_lifecycle as al


class _Q:
    def __init__(self, rows): self.rows = rows
    def __getattr__(self, _): return lambda *a, **k: self
    def execute(self):
        return type("R", (), {"data": self.rows})()


class _C:
    def __init__(self, settings): self.settings = settings
    def table(self, name):
        return _Q(self.settings if name == "admin_settings" else [])


def _v(days, delta):
    return [{"value": json.dumps({"days": days, "expires_at": (datetime.now(timezone.utc) + delta).isoformat(), "reason": "EVAL-01"})}]


def test_override_active():
    assert al.history_days_for_workspace(_C(_v(180, timedelta(days=2))), "w1") == 180


def test_override_expired_falls_back_to_plan():
    assert al.history_days_for_workspace(_C(_v(180, timedelta(days=-1))), "w1") == al.MONTHLY_HISTORY_DAYS


def test_no_override():
    assert al.history_days_for_workspace(_C([]), "w1") == al.MONTHLY_HISTORY_DAYS
