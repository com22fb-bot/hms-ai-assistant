from datetime import date

from app.services import tools_agenda as ta


def test_date_severity_bounds():
    assert ta.date_severity("2026-11-15", date(2026, 11, 7))[0] == "low"
    assert ta.date_severity("2026-11-15", date(2026, 11, 8))[0] == "medium"
    assert ta.date_severity("2026-11-15", date(2026, 11, 16))[0] == "critical"


def test_usage_severity():
    assert ta.usage_severity(None) is None
    assert ta.usage_severity(69.9) == "low"
    assert ta.usage_severity(70) == "medium"
    assert ta.usage_severity(90) == "critical"


def test_money_always_usd_fx_mxn():
    m = ta.money({"cost_usd": 5, "period": "mensual"}, fx=18.81)
    assert (m["usd"], m["fx"], m["mxn"]) == (5.0, 18.81, 94.05)
    m = ta.money({"cost_mxn": 100, "period": "mensual"}, fx=18.81)
    assert m["usd"] == 5.32 and m["mxn"] == 100.0
    m = ta.money({"cost_usd": 5, "period": "mensual"})
    assert m["fx"] == 19.696271 and m["fx_source"] == "open.er-api" and m["mxn"] == 98.48


def test_build_agenda_today_green_and_usage_from_perf():
    perf = {"railway": {"available": True, "cpu_vcpu": 24, "memory_gb": 1},
            "database": {"available": True, "db_size_bytes": 460 * 1048576, "used_pct": 92.0}}
    a = ta.build_agenda(date(2026, 11, 27), perf)
    rows = {r["id"]: r for r in a["rows"]}
    assert rows["railway"]["usage"][0]["pct"] == 50.0
    assert rows["supabase"]["severity"] == "critical"
    assert rows["cloudflare"]["dates"][0]["on"] == "2027-08-07"
    assert rows["railway"]["dates"][0]["on"] == "2026-12-15"
    assert rows["railway"]["dates"][0]["severity"] == "low"
    assert "VENCIDO" not in rows["railway"]["dates"][0]["label"]
    assert rows["cursor"]["dates"][0]["on"] == "2026-12-07"
    assert rows["chatgpt"]["dates"][0]["on"] == "2026-12-09"
    gh_dates = {d["on"]: d for d in rows["github"]["dates"]}
    assert "2026-12-01" not in gh_dates
    assert all("GITHUB_TOKEN_DONEXTO" not in d["label"] for d in rows["github"]["dates"])
    assert "2027-01-20" in gh_dates and "2027-10-21" in gh_dates
    assert "GH_BOT_TOKEN" in gh_dates["2027-10-21"]["label"]
    assert a["next_due"]["on"] == "2026-12-07"
    assert a["status"] == "critical"
    assert a["fx"]["usd_mxn"] == 19.696271
    assert a["fx"]["source"] == "open.er-api"
    assert a["fx"]["date"] == "2026-11-26"


def test_build_agenda_without_perf_railway_green():
    a = ta.build_agenda(date(2026, 11, 27))
    rows = {r["id"]: r for r in a["rows"]}
    assert rows["railway"]["dates"][0]["on"] == "2026-12-15"
    assert rows["railway"]["dates"][0]["severity"] == "low"
    assert a["status"] == "low"
    assert a["alerts"] == []
    assert a["next_due"]["on"] == "2026-12-07"
