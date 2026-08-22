"""Helpers de importación Outlook / Microsoft Graph."""

import unittest

from app.security.identity import MAILBOX_PROVIDERS
from app.services.microsoft_import import (
    decode_microsoft_ref,
    encode_microsoft_ref,
    graph_address,
    graph_address_list,
    is_microsoft_provider,
)


class MicrosoftImportHelpersTest(unittest.TestCase):
    def test_workspace_includes_microsoft_mailbox(self) -> None:
        self.assertIn("microsoft", MAILBOX_PROVIDERS)

    def test_provider_detection(self) -> None:
        self.assertTrue(is_microsoft_provider({"provider": "microsoft"}))
        self.assertTrue(is_microsoft_provider({"provider": "outlook"}))
        self.assertFalse(is_microsoft_provider({"provider": "yahoo"}))

    def test_refs_roundtrip(self) -> None:
        ref = encode_microsoft_ref("inbox", "AAMkAGI2")
        self.assertEqual(decode_microsoft_ref(ref), ("inbox", "AAMkAGI2"))

    def test_graph_address(self) -> None:
        self.assertEqual(
            graph_address(
                {"emailAddress": {"name": "Ana", "address": "ana@outlook.com"}}
            ),
            "Ana <ana@outlook.com>",
        )
        self.assertEqual(
            graph_address_list(
                [
                    {"emailAddress": {"name": "", "address": "a@live.com"}},
                    {"emailAddress": {"name": "B", "address": "b@live.com"}},
                ]
            ),
            "a@live.com, B <b@live.com>",
        )


if __name__ == "__main__":
    unittest.main()
