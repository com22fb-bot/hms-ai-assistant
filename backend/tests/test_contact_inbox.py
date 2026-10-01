"""Contact inbox: admin auth, drafts never send, send only when confirmed."""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_contact import router as admin_contact_router
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services.contact_inbox import (
    DONEXTO_REPLY_FACTS,
    build_reply_instructions,
    hash_contact_ip,
    persist_public_contact,
    schedule_contact_draft,
)
from app.services.support_notify import (
    PUBLIC_CONTACT_INBOX,
    contact_reply_subject,
    send_contact_reply_email,
)

MSG = "11111111-1111-4111-8111-111111111111"


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, store: dict, name: str) -> None:
        self.store = store
        self.name = name
        self.filters: list[tuple[str, object]] = []
        self.op = "select"
        self.payload: dict | None = None
        self.lim: int | None = None
        self.count_exact = False
        self.desc = False
        self.order_col: str | None = None

    def select(self, *_args, count=None, **_kwargs):
        self.op = "select"
        self.count_exact = count == "exact"
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = dict(payload)
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = dict(payload)
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, column, desc=False):
        self.order_col = column
        self.desc = bool(desc)
        return self

    def limit(self, count):
        self.lim = count
        return self

    def _matched(self) -> list[dict]:
        rows = self.store.setdefault(self.name, [])
        return [
            row
            for row in rows
            if all(row.get(column) == value for column, value in self.filters)
        ]

    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self.op == "insert":
            rows.append(self.payload or {})
            return _Result([self.payload])
        matched = self._matched()
        if self.op == "update":
            for row in matched:
                row.update(self.payload or {})
            return _Result(matched)
        if self.order_col:
            matched = sorted(
                matched,
                key=lambda row: row.get(self.order_col) or "",
                reverse=self.desc,
            )
        total = len(matched)
        if self.count_exact:
            data = matched[:1] if self.lim else list(matched)
            return _Result(data, count=total)
        if self.lim is not None:
            matched = matched[: self.lim]
        return _Result(matched)


class FakeSupabase:
    def __init__(self) -> None:
        self.store: dict[str, list] = {}

    def table(self, name: str) -> _Query:
        return _Query(self.store, name)


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthenticationContextMiddleware)
    app.include_router(admin_contact_router)
    return app


def _seed(fake: FakeSupabase, **overrides: object) -> None:
    row = {
        "id": MSG,
        "name": "Alex",
        "email": "alex@example.com",
        "country": "MX",
        "message": "¿Yahoo ya se lee?",
        "language": "es",
        "subject": "Donexto: mensaje de Alex",
        "status": "nuevo",
        "ip_hash": "abc",
        "draft_body": None,
        "draft_error": None,
        "reply_body": None,
        "replied_at": None,
        "created_at": "2026-10-01T12:00:00+00:00",
        "updated_at": "2026-10-01T12:00:00+00:00",
    }
    row.update(overrides)
    fake.store["contact_messages"] = [row]


@contextmanager
def _signed_in(email: str):
    user = SimpleNamespace(id="user-1", email=email, donexto_verified=True)
    context = SimpleNamespace(
        user=user,
        workspace_id="ws-1",
        workspace_name="Donexto",
        membership_role="owner",
        google_account=None,
    )
    with (
        patch.dict(os.environ, {"ADMIN_EMAILS": "hmcelinfo@gmail.com"}),
        patch(
            "app.middleware.authentication_context.authenticate_request",
            return_value=user,
        ),
        patch(
            "app.middleware.authentication_context.resolve_workspace_context",
            return_value=context,
        ),
    ):
        yield


class ContactInboxAuthTests(unittest.TestCase):
    def test_admin_routes_require_a_session(self) -> None:
        request = SimpleNamespace(
            method="GET",
            url=SimpleNamespace(path="/admin/contact-messages"),
        )
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))
        request.url.path = "/admin/contact-messages/x/draft"
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))
        request.method = "POST"
        request.url.path = "/admin/contact-messages/x/send"
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))

    def test_anonymous_request_is_rejected(self) -> None:
        client = TestClient(_app())
        listing = client.get("/admin/contact-messages")
        draft = client.post(f"/admin/contact-messages/{MSG}/draft")
        send = client.post(
            f"/admin/contact-messages/{MSG}/send",
            json={"reply": "Hola", "confirm": True},
        )
        self.assertEqual(listing.status_code, 401)
        self.assertEqual(draft.status_code, 401)
        self.assertEqual(send.status_code, 401)

    def test_signed_in_non_admin_cannot_read_or_send(self) -> None:
        fake = FakeSupabase()
        _seed(fake)
        client = TestClient(_app())
        with (
            _signed_in("otra-persona@example.com"),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
        ):
            listing = client.get("/admin/contact-messages")
            draft = client.post(f"/admin/contact-messages/{MSG}/draft")
            sent = client.post(
                f"/admin/contact-messages/{MSG}/send",
                json={"reply": "Hola", "confirm": True},
            )
        self.assertEqual(listing.status_code, 403)
        self.assertEqual(draft.status_code, 403)
        self.assertEqual(sent.status_code, 403)
        send.assert_not_called()
        self.assertEqual(fake.store["contact_messages"][0]["status"], "nuevo")


class ContactDraftNeverSendsTests(unittest.TestCase):
    def test_unconfigured_model_keeps_manual_reply_and_does_not_send(self) -> None:
        fake = FakeSupabase()
        _seed(fake)
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch.dict(os.environ, {"AI_PROVIDER": "mock", "OPENAI_API_KEY": ""}),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
            patch("app.services.support_notify.httpx.post") as post,
            patch("app.services.support_notify.smtplib.SMTP") as smtp,
        ):
            response = client.post(f"/admin/contact-messages/{MSG}/draft")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "unconfigured")
        self.assertIn("OPENAI_API_KEY", body["message"])
        self.assertEqual(body["contact"]["status"], "nuevo")
        send.assert_not_called()
        post.assert_not_called()
        smtp.assert_not_called()

    def test_ready_draft_is_stored_and_not_sent(self) -> None:
        fake = FakeSupabase()
        _seed(fake)
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch.dict(
                os.environ,
                {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"},
            ),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch(
                "app.services.contact_inbox.generate_reply_text",
                return_value="Hola Alex. Outlook y Hotmail ya están disponibles.",
            ) as generate,
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
            patch("app.services.support_notify.httpx.post") as post,
        ):
            response = client.post(f"/admin/contact-messages/{MSG}/draft")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "draft_ready")
        self.assertEqual(body["contact"]["status"], "borrador listo")
        self.assertIn("Outlook", body["contact"]["draft_body"])
        generate.assert_called_once()
        send.assert_not_called()
        post.assert_not_called()
        self.assertIsNone(fake.store["contact_messages"][0]["reply_body"])

    def test_failed_draft_does_not_send(self) -> None:
        fake = FakeSupabase()
        _seed(fake)
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch.dict(
                os.environ,
                {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"},
            ),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch(
                "app.services.contact_inbox.generate_reply_text",
                side_effect=RuntimeError("boom"),
            ),
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
        ):
            response = client.post(f"/admin/contact-messages/{MSG}/draft")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "draft_failed")
        self.assertEqual(fake.store["contact_messages"][0]["status"], "nuevo")
        send.assert_not_called()

    def test_schedule_skips_when_unconfigured_and_never_sends(self) -> None:
        with (
            patch.dict(os.environ, {"AI_PROVIDER": "mock", "OPENAI_API_KEY": ""}),
            patch("app.services.contact_inbox.threading.Thread") as thread,
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
        ):
            schedule_contact_draft(MSG)
        thread.assert_not_called()
        send.assert_not_called()


class ContactAuthorizeSendTests(unittest.TestCase):
    def test_send_requires_explicit_confirm(self) -> None:
        fake = FakeSupabase()
        _seed(fake, status="borrador listo", draft_body="Borrador")
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch(
                "app.services.contact_inbox.send_contact_reply_email",
                return_value=True,
            ) as send,
        ):
            missing = client.post(
                f"/admin/contact-messages/{MSG}/send",
                json={"reply": "Gracias, Alex."},
            )
            denied = client.post(
                f"/admin/contact-messages/{MSG}/send",
                json={"reply": "Gracias, Alex.", "confirm": False},
            )
            empty = client.post(
                f"/admin/contact-messages/{MSG}/send",
                json={"reply": "   ", "confirm": True},
            )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(empty.status_code, 422)
        send.assert_not_called()
        self.assertEqual(fake.store["contact_messages"][0]["status"], "borrador listo")

    def test_confirm_sends_once_via_resend_and_marks_replied(self) -> None:
        fake = FakeSupabase()
        _seed(fake, status="borrador listo", draft_body="Borrador")
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch(
                "app.services.contact_inbox.send_contact_reply_email",
                return_value=True,
            ) as send,
        ):
            response = client.post(
                f"/admin/contact-messages/{MSG}/send",
                json={"reply": "Gracias, Alex. Outlook ya está disponible.", "confirm": True},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")
        self.assertEqual(response.json()["contact"]["status"], "respondido")
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["to_addr"], "alex@example.com")
        self.assertEqual(
            send.call_args.kwargs["subject"],
            "Re: Donexto: mensaje de Alex",
        )
        self.assertIn("Outlook", send.call_args.kwargs["body"])
        stored = fake.store["contact_messages"][0]
        self.assertEqual(stored["status"], "respondido")
        self.assertEqual(stored["reply_body"], send.call_args.kwargs["body"])

    def test_archive_does_not_send(self) -> None:
        fake = FakeSupabase()
        _seed(fake)
        client = TestClient(_app())
        with (
            _signed_in("hmcelinfo@gmail.com"),
            patch("app.services.contact_inbox._client", return_value=fake),
            patch("app.services.contact_inbox.send_contact_reply_email") as send,
        ):
            response = client.post(f"/admin/contact-messages/{MSG}/archive")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["contact"]["status"], "archivado")
        send.assert_not_called()


class ContactReplyTransportTests(unittest.TestCase):
    def test_reply_uses_resend_http_not_smtp(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "RESEND_API_KEY": "re_test",
                    "SUPPORT_SMTP_HOST": "smtp.resend.com",
                    "SUPPORT_SMTP_FROM": "support@donexto.com",
                },
            ),
            patch("app.services.support_notify.httpx.post") as post,
            patch("app.services.support_notify.smtplib.SMTP") as smtp,
            patch("app.services.support_notify.smtplib.SMTP_SSL") as smtp_ssl,
        ):
            post.return_value = SimpleNamespace(status_code=200)
            delivered = send_contact_reply_email(
                to_addr="alex@example.com",
                subject=contact_reply_subject("Donexto: mensaje de Alex"),
                body="Gracias, Alex.",
            )
        self.assertTrue(delivered)
        smtp.assert_not_called()
        smtp_ssl.assert_not_called()
        self.assertEqual(post.call_args.args[0], "https://api.resend.com/emails")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["from"], f"Donexto <{PUBLIC_CONTACT_INBOX}>")
        self.assertEqual(payload["to"], ["alex@example.com"])
        self.assertEqual(payload["reply_to"], PUBLIC_CONTACT_INBOX)
        self.assertEqual(payload["subject"], "Re: Donexto: mensaje de Alex")
        self.assertNotIn("html", payload)

    def test_reply_subject_does_not_stack(self) -> None:
        self.assertEqual(
            contact_reply_subject("Re: Donexto: mensaje de Alex"),
            "Re: Donexto: mensaje de Alex",
        )

    def test_prompt_includes_product_facts_and_visitor_language(self) -> None:
        instructions = build_reply_instructions("es")
        self.assertIn("Mexican Spanish", instructions)
        self.assertIn("read-only", instructions)
        self.assertIn("Outlook", instructions)
        self.assertIn("Hotmail", instructions)
        self.assertIn("coming soon", instructions)
        self.assertIn("app.donexto.com", instructions)
        self.assertIn(DONEXTO_REPLY_FACTS.splitlines()[0], instructions)

    def test_persist_stores_a_hash_instead_of_the_ip(self) -> None:
        fake = FakeSupabase()
        with patch("app.services.contact_inbox._client", return_value=fake):
            stored = persist_public_contact(
                message_id=MSG,
                name="Alex",
                email="alex@example.com",
                country="MX",
                message="Hola",
                lang="es",
                ip="203.0.113.10",
            )
        self.assertEqual(stored, MSG)
        row = fake.store["contact_messages"][0]
        self.assertNotIn("203.0.113.10", row["ip_hash"])
        self.assertEqual(row["ip_hash"], hash_contact_ip("203.0.113.10"))
        self.assertEqual(row["status"], "nuevo")
        self.assertEqual(row["subject"], "Donexto: mensaje de Alex")


if __name__ == "__main__":
    unittest.main()
