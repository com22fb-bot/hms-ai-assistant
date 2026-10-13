import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import import_categories as ic
from app.services import import_preview as ip


class _Exec:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class _Batch:
    def __init__(self, svc, callback):
        self.svc, self.callback, self.items = svc, callback, []

    def add(self, req, request_id):
        self.items.append(request_id)

    def execute(self):
        for mid in self.items:
            self.svc.calls[mid] = self.svc.calls.get(mid, 0) + 1
            if mid in self.svc.flaky and self.svc.calls[mid] == 1:
                self.callback(mid, None, RuntimeError("429"))
                continue
            self.callback(mid, self.svc.messages_map[mid], None)


class _Service:
    def __init__(self, messages, flaky=()):
        self.messages_map, self.flaky, self.calls, self.formats = messages, set(flaky), {}, []
        self.pages = 0

    def users(self):
        return self

    def messages(self):  # noqa: F811 - API fake
        return self

    def list(self, **kw):
        ids = sorted(self.messages_map)
        start = int(kw.get("pageToken") or 0)
        chunk = ids[start:start + kw["maxResults"]]
        nxt = start + len(chunk)
        page = {"messages": [{"id": i} for i in chunk], "resultSizeEstimate": len(ids)}
        if nxt < len(ids):
            page["nextPageToken"] = str(nxt)
        return _Exec(lambda: page)

    def get(self, **kw):
        self.formats.append((kw["format"], tuple(kw["metadataHeaders"])))
        return object()

    def new_batch_http_request(self, callback):
        return _Batch(self, callback)


def _msg(sender, subject, labels=(), extra=()):
    headers = [{"name": "From", "value": sender}, {"name": "Subject", "value": subject}, *extra]
    return {"payload": {"headers": headers}, "labelIds": list(labels)}


def _service(n, flaky=()):
    data = {}
    for i in range(n):
        kind = i % 4
        if kind == 0:
            data[f"m{i:04d}"] = _msg("CFE <avisos@cfe.mx>", "Tu recibo de luz")
        elif kind == 1:
            data[f"m{i:04d}"] = _msg("Google <no-reply@accounts.google.com>", "Alerta de seguridad")
        elif kind == 2:
            data[f"m{i:04d}"] = _msg("Tienda <news@t.com>", "Novedades", extra=[{"name": "List-Unsubscribe", "value": "<mailto:x>"}])
        else:
            data[f"m{i:04d}"] = _msg("Ana <ana@ejemplo.mx>", "hola")
    svc = _Service({}, flaky)
    svc.messages_map = data
    return svc


class GmailScanTests(unittest.TestCase):
    def _run(self, svc, **kw):
        import app.services.gmail_import_inventory as inv
        orig = inv._service
        inv._service = lambda _c: svc
        orig_sleep = ip.__dict__.get("time")
        try:
            stats = {}
            rows = ip.gmail_headers(object(), 180, stats=stats, **kw)
        finally:
            inv._service = orig
        return rows, stats

    def test_scans_all_eligible_with_pagination_and_retries(self):
        svc = _service(1203, flaky={"m0005", "m0900"})
        rows, stats = self._run(svc)
        self.assertEqual(len(rows), 1203)
        self.assertEqual(stats["total"], 1203)
        self.assertEqual(stats["failed"], 0)
        # Solo metadatos: nunca cuerpo.
        self.assertTrue(all(f == "metadata" for f, _ in svc.formats))
        self.assertIn("List-Unsubscribe", svc.formats[0][1])

    def test_counts_spheres_areas_examples(self):
        rows, stats = self._run(_service(400))
        preview = ip.build_preview(rows, stats["total"])
        self.assertEqual(preview["categories"]["bills"], 100)
        self.assertEqual(preview["categories"]["security"], 100)
        self.assertEqual(preview["categories"]["promos"], 100)
        self.assertEqual(preview["categories"]["other"], 100)
        self.assertEqual(preview["spheres"]["hogar"], 100)
        self.assertEqual(preview["spheres"]["personal"], 100)
        self.assertEqual(preview["scale"], 1.0)
        self.assertTrue(preview["exact"])
        self.assertEqual(preview["examples"]["bills"], ["CFE"])

    def test_cap_extrapolates(self):
        rows, stats = self._run(_service(1200), limit=600)
        preview = ip.build_preview(rows, stats["total"])
        self.assertEqual(preview["sampled"], 600)
        self.assertGreater(preview["scale"], 1.0)
        self.assertFalse(preview["exact"])

    def test_security_never_default_excluded(self):
        self.assertFalse(ic.skip_message([], "Google <no-reply@accounts.google.com>", "Alerta de seguridad"))

    def test_cache(self):
        ip.cache_put("k", {"sampled": 1})
        self.assertEqual(ip.cache_get("k"), {"sampled": 1})
        self.assertIsNone(ip.cache_get("missing"))


if __name__ == "__main__":
    unittest.main()
