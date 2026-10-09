from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException

from app.api import admin_perf
from app.services import runtime_metrics


class ExpenseMathTests(unittest.TestCase):
    def test_monthly_total_and_upcoming(self) -> None:
        rows = [
            {"id": "1", "servicio": "Cursor", "monto": 20, "moneda": "USD", "periodicidad": "mensual", "activo": True, "proximo_cobro": "2026-10-20"},
            {"id": "2", "servicio": "Dominio", "monto": 120, "moneda": "USD", "periodicidad": "anual", "activo": True, "proximo_cobro": "2027-08-01"},
            {"id": "3", "servicio": "SuperGrok", "monto": 10, "moneda": "USD", "periodicidad": "unico", "activo": False, "proximo_cobro": None},
            {"id": "4", "servicio": "Local", "monto": 185, "moneda": "MXN", "periodicidad": "mensual", "activo": True, "proximo_cobro": "2026-11-05"},
        ]
        result = admin_perf.summarize_expenses(rows, 18.5, today=date(2026, 10, 9))
        self.assertEqual(result["monthly_usd"], 40.0)  # 20 + 10 (anual) + 10 (185 MXN)
        self.assertEqual(result["monthly_mxn"], 740.0)
        self.assertEqual([u["servicio"] for u in result["upcoming_30d"]], ["Cursor", "Local"])

    def test_inactive_never_counts(self) -> None:
        row = {"monto": 99, "moneda": "USD", "periodicidad": "mensual", "activo": False}
        self.assertEqual(admin_perf.monthly_usd(row, 18.5), 0.0)


class RuntimeMetricsTests(unittest.TestCase):
    def test_snapshot_percentiles_and_counters(self) -> None:
        for ms in range(1, 101):
            runtime_metrics.record_request("GET /x", float(ms), 200)
        runtime_metrics.record_request("GET /y", 5.0, 500)
        runtime_metrics.bump("direct_access_403")
        snap = runtime_metrics.snapshot()
        self.assertGreaterEqual(snap["p95_ms"], 90)
        self.assertGreater(snap["error_rate_pct"], 0)
        self.assertGreaterEqual(snap["counters"]["direct_access_403"], 1)
        self.assertTrue(any(r["route"] == "GET /x" for r in snap["routes"]))


class AdminGuardTests(unittest.TestCase):
    def test_endpoints_require_admin(self) -> None:
        denied = HTTPException(status_code=403, detail="no")
        with patch.object(admin_perf, "_require_admin", side_effect=denied):
            for call in (admin_perf.admin_performance, admin_perf.admin_list_expenses):
                with self.assertRaises(HTTPException):
                    call()

    def test_missing_tokens_report_steps(self) -> None:
        with patch.dict("os.environ", {"RAILWAY_API_TOKEN": "", "CLOUDFLARE_ANALYTICS_TOKEN": ""}):
            self.assertEqual(admin_perf._railway()["status"], "falta_token")
            cf = admin_perf._cloudflare()
            self.assertEqual(cf["status"], "falta_token")
            self.assertTrue(cf["steps"])


if __name__ == "__main__":
    unittest.main()
