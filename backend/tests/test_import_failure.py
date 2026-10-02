"""Reglas puras para una importación guiada fallida."""

import unittest

from app.services.import_failure import (
    failure_message,
    failure_reason,
    failure_superseded,
)


GRANT = (
    "('invalid_grant: Token has been expired or revoked.', "
    "{'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})"
)


class ImportFailureTest(unittest.TestCase):
    def test_reason_detects_revoked_permission(self) -> None:
        self.assertEqual(failure_reason(GRANT), "auth")
        self.assertEqual(failure_reason("invalid_grant: Bad Request"), "auth")
        self.assertEqual(failure_reason(RuntimeError("AUTHENTICATIONFAILED")), "auth")
        self.assertEqual(failure_reason("HttpError 503 backendError"), "error")
        self.assertEqual(failure_reason(None), "error")

    def test_reconnect_after_failure_supersedes_it(self) -> None:
        job = {
            "status": "failed",
            "last_error": GRANT,
            "completed_at": "2026-09-23 15:23:26.579384+00",
        }
        reconnected = {"updated_at": "2026-10-02T21:44:25.0999+00:00"}
        stale = {"updated_at": "2026-09-20T10:00:00+00:00"}
        self.assertTrue(failure_superseded(job, reconnected))
        self.assertFalse(failure_superseded(job, stale))
        self.assertFalse(failure_superseded(job, {}))

    def test_non_auth_or_non_failed_jobs_are_not_superseded(self) -> None:
        reconnected = {"updated_at": "2026-10-02T21:44:25+00:00"}
        self.assertFalse(
            failure_superseded(
                {"status": "failed", "last_error": "HttpError 500", "completed_at": "2026-09-23T15:23:26+00:00"},
                reconnected,
            )
        )
        self.assertFalse(
            failure_superseded(
                {"status": "completed", "last_error": GRANT, "completed_at": "2026-09-23T15:23:26+00:00"},
                reconnected,
            )
        )
        self.assertFalse(failure_superseded(None, reconnected))

    def test_messages_are_actionable(self) -> None:
        self.assertIn("conectar", failure_message("auth"))
        self.assertIn("Reintentar", failure_message("error"))


if __name__ == "__main__":
    unittest.main()
