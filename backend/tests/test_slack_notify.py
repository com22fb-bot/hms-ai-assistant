from app.services import slack_notify


def test_no_token_is_noop(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert slack_notify._post("#alertas", "x") is False
    slack_notify.post_slack("#alertas", "x")


def test_post_failure_never_raises(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test")

    def boom(*a, **k):
        raise RuntimeError("net")

    monkeypatch.setattr(slack_notify.httpx, "post", boom)
    assert slack_notify._post("#alertas", "x") is False
