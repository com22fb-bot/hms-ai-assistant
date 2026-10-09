from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.security.proxy_gate import ProxyGateMiddleware, client_ip
from app.security import turnstile


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ProxyGateMiddleware)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/auth/google/callback")
    def cb():
        return {"ok": True}

    @app.post("/public/contact")
    def contact():
        return {"ok": True}

    @app.get("/ip")
    def ip(request: Request):
        return {"ip": client_ip(request)}

    return app


class ProxyGateTests(unittest.TestCase):
    def test_no_secret_means_open(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": ""}):
            client = TestClient(_app())
            self.assertEqual(client.post("/public/contact").status_code, 200)

    def test_direct_call_blocked_with_secret(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": "s3cret"}):
            client = TestClient(_app())
            response = client.post("/public/contact")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"]["status"], "direct_access_blocked")
            wrong = client.post("/public/contact", headers={"x-donexto-proxy": "nope"})
            self.assertEqual(wrong.status_code, 403)

    def test_worker_call_allowed(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": "s3cret"}):
            client = TestClient(_app())
            ok = client.post("/public/contact", headers={"x-donexto-proxy": "s3cret"})
            self.assertEqual(ok.status_code, 200)

    def test_health_and_oauth_callback_stay_open(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": "s3cret"}):
            client = TestClient(_app())
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/auth/google/callback").status_code, 200)


class ClientIpTests(unittest.TestCase):
    def _request(self, headers: dict[str, str]):
        req = mock.Mock()
        req.headers = {k.lower(): v for k, v in headers.items()}
        req.client = mock.Mock(host="10.0.0.1")
        return req

    def test_rightmost_forwarded_for_without_proxy(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": ""}):
            req = self._request({"x-forwarded-for": "1.1.1.1, 9.9.9.9"})
            self.assertEqual(client_ip(req), "9.9.9.9")

    def test_spoofed_client_ip_header_ignored_without_secret(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": "s3cret"}):
            req = self._request({"x-donexto-client-ip": "6.6.6.6", "x-forwarded-for": "5.5.5.5"})
            self.assertEqual(client_ip(req), "5.5.5.5")

    def test_worker_client_ip_trusted_with_secret(self) -> None:
        with mock.patch.dict(os.environ, {"HMS_PROXY_SECRET": "s3cret"}):
            req = self._request({"x-donexto-proxy": "s3cret", "x-donexto-client-ip": "7.7.7.7", "x-forwarded-for": "8.8.8.8"})
            self.assertEqual(client_ip(req), "7.7.7.7")


class TurnstileTests(unittest.TestCase):
    def test_not_required_without_secret(self) -> None:
        with mock.patch.dict(os.environ, {"TURNSTILE_SECRET_KEY": ""}):
            self.assertTrue(turnstile.turnstile_passed(""))

    def test_missing_token_rejected_with_secret(self) -> None:
        with mock.patch.dict(os.environ, {"TURNSTILE_SECRET_KEY": "x"}):
            self.assertFalse(turnstile.turnstile_passed(""))

    def test_verify_result_used(self) -> None:
        with mock.patch.dict(os.environ, {"TURNSTILE_SECRET_KEY": "x"}):
            fake = mock.Mock()
            fake.json.return_value = {"success": False, "error-codes": ["invalid-input-response"]}
            with mock.patch.object(turnstile.httpx, "post", return_value=fake):
                self.assertFalse(turnstile.turnstile_passed("tok", "1.2.3.4"))
            fake.json.return_value = {"success": True}
            with mock.patch.object(turnstile.httpx, "post", return_value=fake):
                self.assertTrue(turnstile.turnstile_passed("tok", "1.2.3.4"))


class DiagnosticsAdminOnlyTests(unittest.TestCase):
    def test_env_status_requires_admin(self) -> None:
        from fastapi import HTTPException

        from app.api import system

        with mock.patch(
            "app.api.admin_ops._require_admin",
            side_effect=HTTPException(status_code=403, detail="no"),
        ):
            with self.assertRaises(HTTPException):
                system.env_status()
            with self.assertRaises(HTTPException):
                system.database_health()
