import os
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-only")
from app.security import mailbox_verification as v
from app.middleware import authentication_context as middleware


@pytest.fixture
def setup():
    meta = {"donexto_verified": True, "provider": "azure", "other": "preserve"}
    user = SimpleNamespace(id="user-1", email="mail@outlook.com", raw_app_metadata=meta,
                           donexto_verified=True, has_oauth_identity=True)
    context = SimpleNamespace(user=user, google_account={"email": user.email})
    client = Mock()
    def update(_id, payload):
        meta.update(payload["app_metadata"])
    client.auth.admin.update_user_by_id.side_effect = update
    with patch.object(v, "_admin_user", side_effect=lambda _id: (client, user.email, dict(meta))), patch.object(v, "send_link") as sender:
        yield context, meta, client, sender


def test_oauth_and_legacy_flag_do_not_unlock(setup):
    context, meta, _, _ = setup
    assert not v.context_verified(context)
    meta[v.KEY] = {"email": "different@outlook.com", "method": "email_link", "verified_at": 1}
    assert not v.context_verified(context)


def test_valid_link_is_bound_to_email_and_cannot_be_reused(setup):
    context, meta, _, sender = setup
    assert v.request_verification(context)["status"] == "sent"
    email, token = sender.call_args.args
    assert email == context.user.email
    assert token not in str(meta)
    assert meta[v.PENDING]["hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert v.confirm_verification(context, token)["donexto_verified"]
    assert v.context_verified(context)
    assert meta["other"] == "preserve"
    with pytest.raises(HTTPException):
        v.confirm_verification(context, token)


@pytest.mark.parametrize("failure", ["expired", "wrong_token", "wrong_account"])
def test_invalid_proof_stays_locked(setup, failure):
    context, meta, _, sender = setup
    v.request_verification(context)
    token = sender.call_args.args[1]
    if failure == "expired": meta[v.PENDING]["expires_at"] = 1
    if failure == "wrong_token": token = "x" * 43
    if failure == "wrong_account": meta[v.PENDING]["email"] = "other@outlook.com"
    with pytest.raises(HTTPException): v.confirm_verification(context, token)
    assert not v.context_verified(context)


def test_resend_cooldown_and_delivery_failure(setup):
    context, meta, _, sender = setup
    sender.side_effect = RuntimeError("private SMTP details")
    with pytest.raises(HTTPException) as error: v.request_verification(context)
    assert error.value.status_code == 503
    assert "private SMTP" not in str(error.value.detail)
    assert not v.context_verified(context)
    with pytest.raises(HTTPException) as error: v.request_verification(context)
    assert error.value.status_code == 429


def test_api_cannot_bypass_gate_with_oauth_session(setup):
    context, meta, _, _ = setup
    app = FastAPI()
    app.add_middleware(middleware.AuthenticationContextMiddleware)
    @app.get("/messages")
    def messages(): return {"private": "data"}
    @app.get("/identity/me")
    def identity(): return {"pending": True}
    with patch.object(middleware, "authenticate_request", return_value=context.user), patch.object(middleware, "resolve_workspace_context", return_value=context):
        client = TestClient(app)
        assert client.get("/messages").status_code == 403
        assert client.get("/identity/me").status_code == 200
        meta[v.KEY] = {"email": context.user.email, "method": "email_link", "verified_at": 1}
        assert client.get("/messages").status_code == 200
        context.google_account["email"] = "other@outlook.com"
        assert client.get("/messages").status_code == 409
