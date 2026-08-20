import unittest
from datetime import datetime, timezone
from email.message import EmailMessage

from app.services.yahoo_imap import (
    classify_yahoo_folder,
    decode_yahoo_ref,
    encode_yahoo_ref,
    extract_rfc822_bodies,
    imap_search_date,
    normalize_yahoo_app_password,
    parse_list_mailbox_name,
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

    def test_normalize_keeps_yahoo_password_symbols(self) -> None:
        self.assertEqual(
            normalize_yahoo_app_password("  Clave!Yahoo#2026  "),
            "Clave!Yahoo#2026",
        )
        self.assertEqual(
            normalize_yahoo_app_password("hola-mundo-12"),
            "hola-mundo-12",
        )

    def test_normalize_compacts_sixteen_char_app_code(self) -> None:
        self.assertEqual(
            normalize_yahoo_app_password("abcd efgh ijkl mnop"),
            "abcdefghijklmnop",
        )
        self.assertEqual(
            normalize_yahoo_app_password("abcdefghijklmnop"),
            "abcdefghijklmnop",
        )


if __name__ == "__main__":
    unittest.main()
