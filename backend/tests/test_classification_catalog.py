from app.services.classification_catalog import BANKS, identify_sender
from app.services.classification_catalog.matching import (
    domain_suffix_in,
    match_listed_domain,
)
from app.services.safe_case_classifier import classify_message


def _msg(**kwargs: object) -> dict:
    base: dict = {
        "sender": "",
        "subject": "",
        "body_text": "",
        "labels": ["INBOX"],
        "is_unread": True,
    }
    base.update(kwargs)
    return base


def test_x_com_does_not_match_citibanamex() -> None:
    assert not domain_suffix_in("citibanamex.com", "x.com")
    assert not domain_suffix_in("banamex.com", "x.com")
    assert not domain_suffix_in("banamex.com", "amex.com")
    assert domain_suffix_in("mail.x.com", "x.com")
    assert domain_suffix_in("x.com", "x.com")


def test_citibanamex_is_a_mexican_bank() -> None:
    identity = identify_sender("Alertas Citibanamex <alertas@email.citibanamex.com>")
    assert identity is not None
    assert identity["vertical"] == "bank"
    assert identity["name"] == "Citibanamex / Banamex"
    assert identity["country"] == "MX"


def test_banamex_alert_is_notice_not_social() -> None:
    category, score, reason, actionable = classify_message(
        _msg(
            sender="Banamex <estadosdecuenta@banamex.com>",
            subject="Tu estado de cuenta está listo",
        ),
        existing_case=None,
    )
    assert category == "notice"
    assert actionable is False
    assert score >= 70
    assert "social" not in reason.lower()
    assert "Banamex" in reason or "banco" in reason


def test_gmail_social_label_does_not_override_bank() -> None:
    category, _, reason, _ = classify_message(
        _msg(
            sender="Citibanamex <alertas@citibanamex.com>",
            subject="Compra aprobada por $350.00",
            labels=["INBOX", "CATEGORY_SOCIAL"],
        ),
        existing_case=None,
    )
    assert category == "notice"
    assert "Citibanamex" in reason


def test_real_x_twitter_stays_social() -> None:
    category, _, _, _ = classify_message(
        _msg(
            sender='X <info@x.com>',
            subject="Your weekly summary",
        ),
        existing_case=None,
    )
    assert category == "social"


def test_bank_marketing_is_promotional() -> None:
    category, _, _, _ = classify_message(
        _msg(
            sender="Chase Offers <offers@e.chase.com>",
            subject="Earn 5% cash back this weekend",
        ),
        existing_case=None,
    )
    assert category == "promotional"


def test_amazon_shipment_is_notice() -> None:
    category, _, reason, _ = classify_message(
        _msg(
            sender="Amazon <shipment-tracking@amazon.com>",
            subject="Your order has shipped",
            labels=["INBOX", "CATEGORY_PROMOTIONS"],
        ),
        existing_case=None,
    )
    assert category == "notice"
    assert "Amazon" in reason


def test_aeromexico_reservation_is_notice() -> None:
    category, _, reason, _ = classify_message(
        _msg(
            sender="Aeroméxico <no-reply@aeromexico.com>",
            subject="Tu reservación está confirmada",
        ),
        existing_case=None,
    )
    assert category == "notice"
    assert "Aeroméxico" in reason or "reservación" in reason


def test_linkedin_digest_is_social() -> None:
    category, _, _, _ = classify_message(
        _msg(
            sender="LinkedIn <messages-noreply@linkedin.com>",
            subject="You appeared in 8 searches",
        ),
        existing_case=None,
    )
    assert category == "social"


def test_linkedin_security_code_is_notice() -> None:
    category, _, _, _ = classify_message(
        _msg(
            sender="LinkedIn <security-noreply@linkedin.com>",
            subject="Your verification code is 482193",
            body_text="Usa este código de verificación para entrar.",
        ),
        existing_case=None,
    )
    assert category == "notice"


def test_bank_payment_due_is_action_required() -> None:
    category, _, _, actionable = classify_message(
        _msg(
            sender="BBVA <avisos@bbva.mx>",
            subject="Pago pendiente de tu tarjeta",
            body_text="Tienes un pago pendiente. Payment due on May 12.",
        ),
        existing_case=None,
    )
    assert category == "action_required"
    assert actionable is True


def test_match_does_not_use_bare_com() -> None:
    assert match_listed_domain("random.com", BANKS) is None


def test_no_bank_domain_is_a_social_suffix() -> None:
    from app.services.classification_catalog.social import SOCIAL

    for domain in BANKS:
        for social_domain in SOCIAL:
            assert not domain_suffix_in(domain, social_domain), (
                domain,
                social_domain,
            )
    regions = {meta["region"] for meta in BANKS.values()}
    for needed in ("MX", "US", "CA", "EU", "LATAM"):
        assert needed in regions
    assert "citibanamex.com" in BANKS
    assert "chase.com" in BANKS
    assert "rbc.com" in BANKS
    assert "bancolombia.com" in BANKS
    assert "santander.es" in BANKS
