from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.security import auth_cache, identity

USER_ID = "11111111-1111-4111-8111-111111111111"


def _request(token: str, workspace: str = "") -> SimpleNamespace:
    headers = {"authorization": f"Bearer {token}"}
    if workspace:
        headers["x-hms-workspace-id"] = workspace
    return SimpleNamespace(headers=headers)


def _verified_user(**overrides):
    base = dict(
        id=USER_ID,
        email="a@example.com",
        full_name="A",
        raw_user_metadata={},
        raw_app_metadata={"donexto_verified": True},
        donexto_verified=True,
        has_oauth_identity=False,
    )
    base.update(overrides)
    return identity.AuthenticatedUser(**base)


class LocalJwtTests(unittest.TestCase):
    def setUp(self) -> None:
        auth_cache.clear_all()
        self.key = ec.generate_private_key(ec.SECP256R1())
        signing = SimpleNamespace(key=self.key.public_key())
        self.jwks = MagicMock()
        self.jwks.get_signing_key_from_jwt.return_value = signing
        patcher = patch.object(auth_cache, "_get_jwks_client", return_value=self.jwks)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _token(self, exp_offset: int = 3600, key=None) -> str:
        return jwt.encode(
            {"sub": USER_ID, "exp": int(time.time()) + exp_offset},
            key or self.key,
            algorithm="ES256",
            headers={"kid": "k1"},
        )

    def test_expired_token_rejected_without_calling_supabase(self) -> None:
        with patch.object(identity, "_authenticate_remote") as remote:
            with self.assertRaises(HTTPException) as caught:
                identity.authenticate_request(_request(self._token(exp_offset=-10)))
        self.assertEqual(caught.exception.status_code, 401)
        remote.assert_not_called()

    def test_bad_signature_rejected_without_calling_supabase(self) -> None:
        other = ec.generate_private_key(ec.SECP256R1())
        with patch.object(identity, "_authenticate_remote") as remote:
            with self.assertRaises(HTTPException):
                identity.authenticate_request(_request(self._token(key=other)))
        remote.assert_not_called()

    def test_verified_user_cached_one_remote_call(self) -> None:
        token = self._token()
        with patch.object(identity, "_authenticate_remote", return_value=_verified_user()) as remote:
            for _ in range(5):
                user = identity.authenticate_request(_request(token))
        self.assertEqual(user.id, USER_ID)
        self.assertEqual(remote.call_count, 1)

    def test_unverified_user_is_not_cached(self) -> None:
        token = self._token()
        unverified = _verified_user(donexto_verified=False, raw_app_metadata={})
        with patch.object(identity, "_authenticate_remote", return_value=unverified) as remote:
            identity.authenticate_request(_request(token))
            identity.authenticate_request(_request(token))
        self.assertEqual(remote.call_count, 2)

    def test_jwks_unavailable_falls_back_to_remote(self) -> None:
        self.jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError("down")
        with patch.object(identity, "_authenticate_remote", return_value=_verified_user()) as remote:
            identity.authenticate_request(_request(self._token()))
        remote.assert_called_once()


class ContextCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        auth_cache.clear_all()

    def test_workspace_cached_but_mailbox_always_live(self) -> None:
        user = _verified_user()
        with patch.object(identity, "_resolve_workspace", return_value=("w1", "WS", "owner")) as resolve, \
             patch.object(identity, "_active_mailbox", side_effect=[None, {"id": "acc"}]) as mailbox:
            first = identity.resolve_workspace_context(_request("t"), user)
            second = identity.resolve_workspace_context(_request("t"), user)
        self.assertEqual(resolve.call_count, 1)
        self.assertEqual(mailbox.call_count, 2)
        self.assertIsNone(first.google_account)
        self.assertEqual(second.google_account, {"id": "acc"})
        self.assertEqual(second.workspace_id, "w1")

    def test_cache_is_per_requested_workspace(self) -> None:
        user = _verified_user()
        with patch.object(identity, "_resolve_workspace", return_value=("w1", "WS", "owner")) as resolve, \
             patch.object(identity, "_active_mailbox", return_value=None):
            identity.resolve_workspace_context(_request("t"), user)
            identity.resolve_workspace_context(_request("t", workspace="w2"), user)
        self.assertEqual(resolve.call_count, 2)

    def test_forbidden_is_not_cached(self) -> None:
        user = _verified_user()
        error = HTTPException(status_code=403, detail="no")
        with patch.object(identity, "_resolve_workspace", side_effect=error) as resolve, \
             patch.object(identity, "_active_mailbox", return_value=None):
            for _ in range(2):
                with self.assertRaises(HTTPException):
                    identity.resolve_workspace_context(_request("t"), user)
        self.assertEqual(resolve.call_count, 2)


class RuleBackgroundTests(unittest.TestCase):
    def test_apply_existing_is_scheduled_not_run_inline(self) -> None:
        from app.services import message_rules_service as svc

        context = SimpleNamespace(workspace_id="w1", user=SimpleNamespace(id=USER_ID))
        created = {"id": "r1", "account_id": "acc", "workspace_id": "w1", "target_category": "updates"}
        storage = MagicMock()
        scheduled = []
        with patch.object(svc, "require_google_account", return_value=(context, {"id": "acc"})), \
             patch.object(svc, "OAuthStorage", return_value=storage), \
             patch.object(svc, "_message_or_404", return_value={"subject": "s"}), \
             patch.object(svc, "_derived_values", return_value=("x", None)), \
             patch.object(svc, "_first", return_value=created), \
             patch.object(svc, "apply_rule_to_existing") as apply_now:
            result = svc.create_classification_rule(
                source_message_id="m1",
                name="r",
                match_type=next(iter(svc.RULE_TYPES)),
                target_category=next(iter(svc.RULE_CATEGORIES)),
                explicit_value=None,
                apply_existing=True,
                notify_push=False,
                schedule=lambda fn, *args: scheduled.append((fn, args)),
            )
            apply_now.assert_not_called()
            self.assertTrue(result["applying_in_background"])
            self.assertEqual(len(scheduled), 1)
            fn, args = scheduled[0]
            fn(*args)
            apply_now.assert_called_once_with(rule=created)


if __name__ == "__main__":
    unittest.main()
