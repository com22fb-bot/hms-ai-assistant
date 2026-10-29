from datetime import date, datetime, timezone

from app.services.vendor_payments import PAID, payment_status, vendor_payment_items


def test_semaforo():
    t = date(2026, 11, 8)
    assert payment_status("2026-11-15", t) == ("medium", 7)
    assert payment_status("2026-11-16", t) == ("low", 8)
    assert payment_status("2026-11-08", t) == ("medium", 0)
    assert payment_status("2026-11-07", t)[0] == "critical"


def test_items_and_invalid():
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    items = vendor_payment_items(now)
    assert items[0]["severity"] == "medium" and "vence en 5" in items[0]["title"]
    bad = vendor_payment_items(now, [{"vendor": "X", "due_on": "nope", "amount_usd": 1}, {"vendor": "Y"}])
    assert [i["id"] for i in bad] == ["pago:invalido:X", "pago:invalido:Y"]
    over = vendor_payment_items(datetime(2026, 11, 16, tzinfo=timezone.utc))
    assert over[0]["severity"] == "critical" and "VENCIDO" in over[0]["title"]


def test_railway_paid_registered():
    assert any(p["vendor"] == "Railway" and p["amount_usd"] == 5.0 for p in PAID)
