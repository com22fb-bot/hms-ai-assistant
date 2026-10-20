"""Gmail IMAP con contraseña de aplicación: login validado, cifrado, sin logs del secreto."""

from __future__ import annotations

import imaplib
import logging
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from fastapi import HTTPException

from app.api.gmail_imap_mail import GmailImapConnectRequest, gmail_imap_connect
from app.services.gmail_imap import (
    GmailImapError,
    classify_gmail_auth_error,
    normalize_gmail_app_password,
)
from app.services.guided_import_job_service import is_icloud_provider, _app_password_provider
from app.services.imap_provider import GMAIL_IMAP
from app.services.icloud_imap import IcloudImapError
from app.services.oauth_storage import OAuthStorage, _decrypt
from app.services.yahoo_import import _provider_label


APP_PASSWORD = "abcd efgh ijkl mnop"
APP_PASSWORD_COMPACT = "abcdefghijklmnop"
ADDRESS = "hector@gmail.com"

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



class GmailImapTests(unittest.TestCase):
    def test_config_is_gmail_ssl(self) -> None:
        self.assertEqual((GMAIL_IMAP.host, GMAIL_IMAP.port), ("imap.gmail.com", 993))
        self.assertEqual(GMAIL_IMAP.auth_mode, "password")

    def test_normalize_strips_spaces(self) -> None:
        self.assertEqual(normalize_gmail_app_password(APP_PASSWORD), APP_PASSWORD_COMPACT)
        self.assertEqual(normalize_gmail_app_password("abcd-efgh-ijkl-mnop"), APP_PASSWORD_COMPACT)

    def test_same_pipeline_as_icloud(self) -> None:
        account = {"provider": "gmail_imap"}
        self.assertTrue(is_icloud_provider(account))
        self.assertEqual(_app_password_provider(account), "gmail_imap")
        self.assertEqual(_provider_label("gmail_imap"), "Gmail")
        self.assertTrue(issubclass(GmailImapError, IcloudImapError))

    def test_connect_validates_then_encrypts(self) -> None:
        fake_imap = _Imap()
        client = _Client()
        storage = OAuthStorage(client=client)
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            with (
                patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap) as ssl,
                patch("app.api.gmail_imap_mail.allow_request", return_value=True),
                patch("app.api.gmail_imap_mail.oauth_storage", storage),
                patch(
                    "app.api.gmail_imap_mail.mint_yahoo_session_or_http",
                    return_value={"user_id": "user-1", "workspace_id": "ws-1", "access_token": "s"},
                ),
            ):
                result = gmail_imap_connect(
                    GmailImapConnectRequest(email=ADDRESS, app_password=APP_PASSWORD),
                    _Request(),  # type: ignore[arg-type]
                )
        finally:
            root.removeHandler(handler)
        self.assertEqual(ssl.call_args.args[:2], ("imap.gmail.com", 993))
        self.assertTrue(result.connected)
        self.assertEqual(result.provider, "gmail_imap")
        self.assertEqual(fake_imap.password, APP_PASSWORD_COMPACT)
        self.assertTrue(fake_imap.readonly)
        stored = str(client.store.creds[0]["access_token"])
        self.assertNotIn(APP_PASSWORD_COMPACT, stored)
        self.assertEqual(_decrypt(stored), APP_PASSWORD_COMPACT)
        self.assertEqual(client.store.creds[0]["metadata"]["host"], "imap.gmail.com")
        self.assertEqual(client.store.accounts[0]["provider"], "gmail_imap")
        self.assertNotIn(APP_PASSWORD_COMPACT, "\n".join(records))

    def test_wrong_password_not_saved(self) -> None:
        fake_imap = _Imap(login_error=b"[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
        client = _Client()
        with (
            patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap),
            patch("app.api.gmail_imap_mail.allow_request", return_value=True),
            patch("app.api.gmail_imap_mail.oauth_storage", OAuthStorage(client=client)),
        ):
            with self.assertRaises(HTTPException) as caught:
                gmail_imap_connect(
                    GmailImapConnectRequest(email=ADDRESS, app_password=APP_PASSWORD),
                    _Request(),  # type: ignore[arg-type]
                )
        self.assertEqual(caught.exception.detail["code"], "wrong_password")
        self.assertNotIn(APP_PASSWORD_COMPACT, str(caught.exception.detail))
        self.assertEqual(client.store.creds, [])

    def test_normal_password_asks_for_app_password(self) -> None:
        error = classify_gmail_auth_error(
            "[ALERT] Application-specific password required", "MiClave123"
        )
        self.assertEqual(error.code, "app_password_required")
        self.assertNotIn("MiClave123", str(error))


    def test_normalize_strips_unicode_and_invisible(self) -> None:
        pasted = "\u200babcd\u00a0efgh\u2009ijkl\u3000mnop\ufeff\n"
        self.assertEqual(normalize_gmail_app_password(pasted), APP_PASSWORD_COMPACT)
        self.assertEqual(normalize_gmail_app_password(" abcd\tefgh\u202fijkl\u2060mnop "), APP_PASSWORD_COMPACT)
        # Ancho completo (teclados asiáticos) → ASCII.
        self.assertEqual(normalize_gmail_app_password("ａｂｃｄ efgh ijkl mnop"), APP_PASSWORD_COMPACT)
        # Aunque no sean 16 letras, nunca se envían espacios.
        self.assertEqual(normalize_gmail_app_password("abcd efgh ijkl mno"), "abcdefghijklmno")

    def test_case_is_preserved(self) -> None:
        self.assertEqual(normalize_gmail_app_password("ABCD efgh IJKL mnop"), "ABCDefghIJKLmnop")

    def test_login_sends_full_address_and_compact_secret(self) -> None:
        fake_imap = _Imap()
        with patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap):
            from app.services.gmail_imap import verify_gmail_imap_login

            verify_gmail_imap_login(" Hector@Gmail.com ", "\u200babcd\u00a0efgh ijkl mnop")
        self.assertEqual(fake_imap.user, "hector@gmail.com")
        self.assertEqual(fake_imap.password, APP_PASSWORD_COMPACT)

    def test_non_ascii_secret_is_rejected_before_login(self) -> None:
        from app.services.gmail_imap import verify_gmail_imap_login

        fake_imap = _Imap()
        with patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap):
            with self.assertRaises(GmailImapError) as caught:
                verify_gmail_imap_login(ADDRESS, "abcdéfghijklmnop")
        self.assertEqual(caught.exception.code, "invalid_characters")
        self.assertIsNone(fake_imap.password)

    def test_error_mapping_is_precise(self) -> None:
        cases = {
            "[AUTHENTICATIONFAILED] Invalid credentials (Failure)": "wrong_password",
            "[ALERT] Application-specific password required: https://support.google.com/accounts/answer/185833 (Failure)": "app_password_required",
            "[ALERT] Please log in via your web browser: https://support.google.com/mail/accounts/answer/78754 (Failure)": "web_login_required",
            "[WEBLOGINREQUIRED] Web login required": "web_login_required",
            "[ALERT] Your account is not enabled for IMAP use.": "imap_disabled",
            "[ALERT] Too many simultaneous connections. (Failure)": "rate_limited",
            "something else": "imap_failed",
        }
        for server, code in cases.items():
            error = classify_gmail_auth_error(f"b'{server}'", APP_PASSWORD_COMPACT)
            self.assertEqual(error.code, code, server)
            self.assertNotIn(APP_PASSWORD_COMPACT, str(error))

    def test_failure_log_has_server_text_but_no_secret(self) -> None:
        fake_imap = _Imap(login_error=f"[AUTHENTICATIONFAILED] Invalid credentials {APP_PASSWORD_COMPACT}".encode())
        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Capture()
        logging.getLogger().addHandler(handler)
        try:
            with (
                patch("app.services.imap_mail.imaplib.IMAP4_SSL", return_value=fake_imap),
                patch("app.api.gmail_imap_mail.allow_request", return_value=True),
            ):
                with self.assertRaises(HTTPException):
                    gmail_imap_connect(
                        GmailImapConnectRequest(email=ADDRESS, app_password=APP_PASSWORD),
                        _Request(),  # type: ignore[arg-type]
                    )
        finally:
            logging.getLogger().removeHandler(handler)
        blob = "\n".join(records)
        self.assertIn("AUTHENTICATIONFAILED", blob)
        self.assertIn("code=wrong_password", blob)
        self.assertNotIn(APP_PASSWORD_COMPACT, blob)


if __name__ == "__main__":
    unittest.main()
