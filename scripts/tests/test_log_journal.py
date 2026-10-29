import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from log_journal import redact, useful, expired_prefixes, day_window

class T(unittest.TestCase):
    def test_redact(self):
        s = redact("user ana.p@x.com token=abc123 Bearer eyJa.b.c postgres://u:pw@h/db sk-ABCDEFGH12345 +52 55 1234 5678")
        for bad in ("ana.p@x.com", "abc123", "eyJa", ":pw@", "sk-ABCDEFGH", "1234 5678"):
            assert bad not in s, s

    def test_useful(self):
        assert useful("error", "x") and useful("info", "IMAP fetch failed") and not useful("info", "GET / 200")

    def test_retention(self):
        p = ["logs/2026-07-01/", "logs/2026-08-01/", "logs/2026-10-28/", "db/x", "logs/../"]
        assert expired_prefixes(p, "2026-10-29") == ["logs/2026-07-01/"]

    def test_window(self):
        assert day_window("2026-10-28") == ("2026-10-28T00:00:00Z", "2026-10-29T00:00:00Z")
