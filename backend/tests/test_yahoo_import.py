import unittest
from datetime import datetime, timezone
from email.message import EmailMessage

from app.services.yahoo_imap import (
    classify_yahoo_folder,
    decode_yahoo_ref,
    encode_yahoo_ref,
    extract_rfc822_bodies,
    imap_search_date,
    parse_list_mailbox_name,
    YahooImapError,
    assert_address_allowed_for_brand,
    normalize_imap_brand,
    safe_imap_host,
)


class YahooImportHelpersTest(unittest.TestCase):
    def test_imap_search_date_uses_english_months(self) -> None:
        stamp = datetime(2026, 2, 18, tzinfo=timezone.utc)
        self.assertEqual(imap_search_date(stamp), "18-Feb-2026")

    def test_classify_yahoo_folders(self) -> None:
        self.assertEqual(classify_yahoo_folder("INBOX"), "inbox")
        self.assertEqual(classify_yahoo_folder("Sent"), "sent")
        self.assertEqual(classify_yahoo_folder("Bulk Mail"), "spam")
        self.assertEqual(classify_yahoo_folder("Trash"), "trash")
        self.assertEqual(classify_yahoo_folder("Draft"), "draft")
        self.assertEqual(classify_yahoo_folder("Archive"), "other")

    def test_parse_list_mailbox_name_quoted(self) -> None:
        raw = b'(\\HasNoChildren) "/" "Sent Mail"'
        self.assertEqual(parse_list_mailbox_name(raw), "Sent Mail")

    def test_yahoo_refs_roundtrip(self) -> None:
        ref = encode_yahoo_ref("INBOX", "12345")
        self.assertEqual(decode_yahoo_ref(ref), ("INBOX", "12345"))
        self.assertEqual(decode_yahoo_ref("INBOX:99"), ("INBOX", "99"))

    def test_extract_rfc822_plain_body(self) -> None:
        message = EmailMessage()
        message["Subject"] = "Factura"
        message["From"] = "Cobranza <billing@example.com>"
        message.set_content("Pago pendiente de agosto")
        text, html, has_attachments = extract_rfc822_bodies(message)
        self.assertIn("Pago pendiente", text)
        self.assertEqual(html, "")
        self.assertFalse(has_attachments)


class CompanyDomainImapPolicyTest(unittest.TestCase):
    def test_outlook_accepts_private_company_domain(self) -> None:
        assert_address_allowed_for_brand("hector@acme-industria.mx", "outlook")

    def test_apple_accepts_icloud_plus_custom_domain(self) -> None:
        assert_address_allowed_for_brand("correo@familia.mx", "apple")

    def test_yahoo_rejects_company_domain(self) -> None:
        with self.assertRaises(YahooImapError):
            assert_address_allowed_for_brand("hector@acme-industria.mx", "yahoo")

    def test_aol_maps_from_yahoo_brand(self) -> None:
        self.assertEqual(
            normalize_imap_brand("yahoo", "hsalcidor@aol.com"),
            "aol",
        )

    def test_company_brand_aliases(self) -> None:
        self.assertEqual(normalize_imap_brand("empresa", "ti@fabrica.com"), "company")
        self.assertEqual(normalize_imap_brand("m365", "ti@fabrica.com"), "outlook")

    def test_safe_imap_host_rejects_localhost_and_ips(self) -> None:
        with self.assertRaises(YahooImapError):
            safe_imap_host("localhost")
        with self.assertRaises(YahooImapError):
            safe_imap_host("127.0.0.1")
        with self.assertRaises(YahooImapError):
            safe_imap_host("")


if __name__ == "__main__":
    unittest.main()
