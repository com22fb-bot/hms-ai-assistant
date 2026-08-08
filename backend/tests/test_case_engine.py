from app.services.case_engine import normalize_subject


def test_normalize_subject_removes_reply_prefixes() -> None:
    assert (
        normalize_subject("RE: FWD: Factura 005")
        == "factura 005"
    )


def test_normalize_subject_collapses_whitespace() -> None:
    assert (
        normalize_subject("  Solicitud   de   pago  ")
        == "solicitud de pago"
    )


def test_normalize_subject_keeps_business_identifiers() -> None:
    assert (
        normalize_subject("Caso #ABC-123 / Pago")
        == "caso #abc-123 / pago"
    )
