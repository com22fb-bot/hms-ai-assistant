"""iCloud IMAP: conexión, solo lectura, cifrado y desconexión."""

from __future__ import annotations

import imaplib
import logging
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.api.icloud_mail import (
    IcloudConnectRequest,
    icloud_connect,
    icloud_disconnect,
)
from app.services.icloud_imap import (
    classify_icloud_auth_error,
    list_icloud_messages,
    normalize_icloud_app_password,
    verify_icloud_login,
)
from app.services.imap_provider import PEEK_FULL_SPEC, PEEK_HEADER_SPEC
from app.services.oauth_storage import OAuthStorage, _decrypt


APP_PASSWORD = "abcd-efgh-ijkl-mnop"
APP_PASSWORD_COMPACT = "abcdefghijklmnop"
ADDRESS = "ana@icloud.com"


class _Resp:
    def __init__(self, data: object) -> None:
        self.data = data


class _Store:
    def __init__(self) -> None:
        self.accounts: list[dict] = []
        self.creds: list[dict] = []


class _Query:
    def __init__(self, store: _Store, table: str) -> None:
        self.store = store
        self.table = table
        self.op = "select"
        self.payload: dict | None = None
        self.eqs: dict[str, object] = {}

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        self.op = "select"
        return self

    def insert(self, payload: dict) -> _Query:
        self.op = "insert"
        self.payload = dict(payload)
        return self

    def update(self, payload: dict) -> _Query:
        self.op = "update"
        self.payload = dict(payload)
        return self

    def delete(self) -> _Query:
        self.op = "delete"
        return self

    def eq(self, key: str, value: object) -> _Query:
        self.eqs[key] = value
        return self

    def neq(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def limit(self, _count: int) -> _Query:
        return self

    def order(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def execute(self) -> _Resp:
        if self.table == "communication_accounts":
            if self.op == "select":
                rows = [
                    row
                    for row in self.store.accounts
                    if all(row.get(key) == value for key, value in self.eqs.items())
                ]
                return _Resp(rows[:1])
            if self.op == "insert" and self.payload is not None:
                row = {"id": "acc-icloud", **self.payload}
                self.store.accounts.append(row)
                return _Resp([row])
            if self.op == "update" and self.payload is not None:
                for row in self.store.accounts:
                    if not self.eqs or all(
                        row.get(key) == value for key, value in self.eqs.items()
                    ):
                        row.update(self.payload)
                        return _Resp([row])
                return _Resp([])
        if self.table == "oauth_credentials":
            if self.op == "select":
                rows = [
                    row
                    for row in self.store.creds
                    if row.get("account_id") == self.eqs.get("account_id")
                ]
                return _Resp(rows[:1])
            if self.op == "insert" and self.payload is not None:
                row = {"id": "cred-icloud", **self.payload}
                self.store.creds.append(row)
                return _Resp([row])
            if self.op == "update" and self.payload is not None:
                for row in self.store.creds:
                    if row.get("account_id") == self.eqs.get("account_id"):
                        row.update(self.payload)
                        return _Resp([row])
                return _Resp([])
            if self.op == "delete":
                before = list(self.store.creds)
                self.store.creds = [
                    row
                    for row in self.store.creds
                    if row.get("account_id") != self.eqs.get("account_id")
                ]
                return _Resp(before[:1] or [{"deleted": True}])
        return _Resp([])


class _Client:
    def __init__(self) -> None:
        self.store = _Store()

    def table(self, name: str) -> _Query:
        return _Query(self.store, name)


class _Imap:
    def __init__(self, login_error: bytes | None = None) -> None:
        self.login_error = login_error
        self.readonly: bool | None = None
        self.mailbox: str | None = None
        self.fetches: list[object] = []
        self.password: str | None = None
        self.user: str | None = None
        self.store_called = False
        self.logged_out = False

    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        self.user = user
        self.password = password
        if self.login_error is not None:
            raise imaplib.IMAP4.error(self.login_error)
        return "OK", [b"logged-in"]

    def select(self, mailbox: str = "INBOX", readonly: bool = False):
        self.mailbox = mailbox
        self.readonly = readonly
        return "OK", [b"2"]

    def search(self, _charset: object, *_criteria: object):
        return "OK", [b"10 11"]

    def fetch(self, _num: object, spec: object):
        self.fetches.append(spec)
        raw = (
            b"Subject: Cita medica\r\n"
            b"From: Clinica <citas@example.com>\r\n"
            b"To: ana@icloud.com\r\n"
            b"Date: Thu, 01 Oct 2026 15:00:00 +0000\r\n"
            b"\r\n"
        )
        return "OK", [(b"11 (FLAGS () BODY[HEADER]", raw), b")"]

    def store(self, *_args: object, **_kwargs: object) -> None:
        self.store_called = True
        raise AssertionError("iCloud no debe modificar flags")

    def uid(self, command: str, *args: object):
        if command == "FETCH":
            spec = args[-1] if args else ""
            self.fetches.append(spec)
            if "BODY.PEEK" not in str(spec):
                raise AssertionError(spec)
        return "OK", [b""]

    def logout(self) -> tuple[str, list[bytes]]:
        self.logged_out = True
        return "BYE", [b""]


class _Request:
    def __init__(self, host: str = "203.0.113.9") -> None:
        self.headers: dict[str, str] = {}
        self.client = type("C", (), {"host": host})()


class IcloudImapTests(unittest.TestCase):
    def test_normalize_app_password_strips_groups(self) -> None:
        self.assertEqual(
            normalize_icloud_app_password(" abcd-efgh-ijkl-mnop "),
            APP_PASSWORD_COMPACT,
        )
        self.assertEqual(
            normalize_icloud_app_password("Mi clave Apple"),
            "Mi clave Apple",
        )

    def test_connect_success_is_readonly_and_encrypts_secret(self) -> None:
        fake_imap = _Imap()
        client = _Client()
        storage = OAuthStorage(client=client)
        request = _Request()
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            with (
                patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap),
                patch("app.api.icloud_mail.allow_request", return_value=True),
                patch("app.api.icloud_mail.oauth_storage", storage),
                patch(
                    "app.api.icloud_mail.mint_yahoo_session_or_http",
                    return_value={
                        "user_id": "user-1",
                        "workspace_id": "ws-1",
                        "access_token": "session-access",
                        "refresh_token": "session-refresh",
                        "expires_in": "3600",
                    },
                ),
            ):
                result = icloud_connect(
                    IcloudConnectRequest(email=ADDRESS, app_password=APP_PASSWORD),
                    request,  # type: ignore[arg-type]
                )
        finally:
            root.removeHandler(handler)

        self.assertTrue(result.connected)
        self.assertEqual(result.email, ADDRESS)
        self.assertEqual(result.access_token, "session-access")
        self.assertEqual(fake_imap.user, ADDRESS)
        self.assertEqual(fake_imap.password, APP_PASSWORD_COMPACT)
        self.assertTrue(fake_imap.readonly)
        self.assertEqual(fake_imap.mailbox, "INBOX")
        self.assertFalse(fake_imap.store_called)
        self.assertTrue(fake_imap.logged_out)
        self.assertEqual(len(client.store.creds), 1)
        stored = str(client.store.creds[0]["access_token"])
        self.assertNotIn(APP_PASSWORD_COMPACT, stored)
        self.assertNotIn(APP_PASSWORD, stored)
        self.assertEqual(_decrypt(stored), APP_PASSWORD_COMPACT)
        metadata = client.store.creds[0]["metadata"]
        self.assertEqual(metadata["auth"], "app_password")
        self.assertEqual(metadata["host"], "imap.mail.me.com")
        self.assertTrue(metadata["readonly"])
        self.assertNotIn("app_password", metadata)
        blob = "\n".join(records)
        self.assertNotIn(APP_PASSWORD, blob)
        self.assertNotIn(APP_PASSWORD_COMPACT, blob)

    def test_list_uses_body_peek_and_examine(self) -> None:
        fake_imap = _Imap()
        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            return_value=fake_imap,
        ):
            messages = list_icloud_messages(ADDRESS, APP_PASSWORD, max_results=5)
        self.assertTrue(fake_imap.readonly)
        self.assertEqual(fake_imap.fetches, [PEEK_HEADER_SPEC, PEEK_HEADER_SPEC])
        self.assertIn("BODY.PEEK", PEEK_HEADER_SPEC)
        self.assertNotIn("BODY[", PEEK_HEADER_SPEC.replace("BODY.PEEK", ""))
        self.assertIn("BODY.PEEK", PEEK_FULL_SPEC)
        self.assertEqual(messages[0]["subject"], "Cita medica")
        self.assertIn("ICLOUD", messages[0]["labels"])
        self.assertFalse(fake_imap.store_called)

    def test_wrong_app_password(self) -> None:
        fake_imap = _Imap(login_error=b"[AUTHENTICATIONFAILED] Authentication failed")
        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            return_value=fake_imap,
        ):
            with self.assertRaises(HTTPException) as caught:
                icloud_connect(
                    IcloudConnectRequest(
                        email=ADDRESS,
                        app_password=APP_PASSWORD,
                    ),
                    _Request("203.0.113.10"),  # type: ignore[arg-type]
                )
        detail = caught.exception.detail
        self.assertIsInstance(detail, dict)
        self.assertEqual(detail["code"], "wrong_password")
        self.assertNotIn(APP_PASSWORD_COMPACT, str(detail))

    def test_regular_password_asks_for_app_password(self) -> None:
        fake_imap = _Imap(login_error=b"[AUTHENTICATIONFAILED] Authentication failed")
        with (
            patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap),
            patch("app.api.icloud_mail.allow_request", return_value=True),
        ):
            with self.assertRaises(HTTPException) as caught:
                icloud_connect(
                    IcloudConnectRequest(
                        email="ana@me.com",
                        app_password="MiClaveDeApple1",
                    ),
                    _Request("203.0.113.11"),  # type: ignore[arg-type]
                )
        detail = caught.exception.detail
        self.assertEqual(detail["code"], "app_password_required")
        self.assertNotIn("MiClaveDeApple1", str(detail))

    def test_two_factor_required_when_apple_asks_for_browser(self) -> None:
        error = classify_icloud_auth_error(
            "Please log in via your web browser: https://appleid.apple.com",
            APP_PASSWORD_COMPACT,
        )
        self.assertEqual(error.code, "two_factor_required")
        self.assertNotIn(APP_PASSWORD_COMPACT, str(error))

    def test_verify_examine_is_readonly(self) -> None:
        fake_imap = _Imap()
        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            return_value=fake_imap,
        ):
            verified = verify_icloud_login("Ana@mac.com", APP_PASSWORD)
        self.assertEqual(verified, "ana@mac.com")
        self.assertTrue(fake_imap.readonly)
        self.assertEqual(fake_imap.mailbox, "INBOX")

    def test_disconnect_deletes_credentials(self) -> None:
        client = _Client()
        client.store.accounts.append(
            {
                "id": "acc-icloud",
                "provider": "icloud",
                "email": ADDRESS,
                "status": "active",
            }
        )
        client.store.creds.append(
            {
                "id": "cred-icloud",
                "account_id": "acc-icloud",
                "access_token": "ciphertext",
            }
        )
        storage = OAuthStorage(client=client)
        context = type(
            "Ctx",
            (),
            {
                "google_account": {
                    "id": "acc-icloud",
                    "provider": "icloud",
                    "email": ADDRESS,
                }
            },
        )()
        with (
            patch("app.api.icloud_mail.require_request_context", return_value=context),
            patch("app.api.icloud_mail.oauth_storage", storage),
        ):
            status = icloud_disconnect()
        self.assertFalse(status.connected)
        self.assertEqual(client.store.creds, [])
        self.assertEqual(client.store.accounts[0]["status"], "disconnected")


if __name__ == "__main__":
    unittest.main()
