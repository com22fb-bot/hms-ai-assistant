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


class _HttpErr(Exception):
    def __init__(self, status):
        super().__init__(str(status))
        self.resp = type("R", (), {"status": status})()
        self.content = b""


class _Batch:
    def __init__(self, svc, callback):
        self.svc, self.callback, self.items = svc, callback, []

    def add(self, req, request_id):
        assert len(self.items) < ip._BATCH
        self.items.append(request_id)

    def execute(self):
        for mid in self.items:
            self.svc.calls[mid] = self.svc.calls.get(mid, 0) + 1
            if mid in self.svc.flaky and self.svc.calls[mid] == 1:
                self.callback(mid, None, RuntimeError("429"))
                continue
            if mid in self.svc.broken:
                self.callback(mid, None, _HttpErr(404))
                continue
            self.callback(mid, self.svc.messages_map[mid], None)


class _Service:
    def __init__(self, messages, flaky=(), broken=()):
        self.messages_map, self.flaky, self.calls, self.formats = messages, set(flaky), {}, []
        self.broken = set(broken)
        self.batch_sizes = []
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
        self.formats.append((kw["format"], tuple(kw["metadataHeaders"]), kw.get("fields")))
        return object()

    def new_batch_http_request(self, callback):
        return _Batch(self, callback)


def _msg(sender, subject, labels=(), extra=()):
    headers = [{"name": "From", "value": sender}, {"name": "Subject", "value": subject}, *extra]
    return {"payload": {"headers": headers}, "labelIds": list(labels)}


def _service(n, flaky=(), broken=()):
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
    svc = _Service({}, flaky, broken)
    svc.messages_map = data
    return svc


class GmailScanTests(unittest.TestCase):
    def _run(self, svc, **kw):
        import app.services.gmail_import_inventory as inv
        orig = inv._service
        inv._service = lambda _c: svc
        try:
            stats = {}
            self.sleeps = []
            rows = ip.gmail_headers(object(), 180, stats=stats, sleep=self.sleeps.append, **kw)
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
        self.assertTrue(all(f == "metadata" for f, _, _ in svc.formats))
        self.assertTrue(all(fields == "labelIds,payload/headers" for _, _, fields in svc.formats))
        # Ritmo controlado entre lotes (concurrencia limitada).
        self.assertTrue(any(w > 0 for w in self.sleeps))
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

    def test_permanent_errors_not_retried(self):
        svc = _service(100, broken={"m0003"})
        rows, stats = self._run(svc)
        self.assertEqual(len(rows), 99)
        self.assertEqual(svc.calls["m0003"], 1)
        self.assertEqual(stats["failed"], 1)

    def test_cap_extrapolates(self):
        rows, stats = self._run(_service(1200), limit=600)
        preview = ip.build_preview(rows, stats["total"])
        self.assertEqual(preview["sampled"], 600)
        self.assertGreater(preview["scale"], 1.0)
        self.assertFalse(preview["exact"])

    def test_security_never_default_excluded(self):
        self.assertFalse(ic.skip_message([], "Google <no-reply@accounts.google.com>", "Alerta de seguridad"))

    def test_cache_isolated_and_aggregate_only(self):
        a = ip.cache_key("ws1", "acc1", 180)
        b = ip.cache_key("ws2", "acc1", 180)
        ip.cache_put(a, {"sampled": 5, "categories": {"bills": 5}, "subjects": ["secreto"], "ids": ["m1"]}, now=1000)
        self.assertEqual(ip.cache_get(a, now=1001), {"sampled": 5, "categories": {"bills": 5}})
        self.assertIsNone(ip.cache_get(b, now=1001))
        self.assertIsNone(ip.cache_get(a, now=1000 + ip.CACHE_TTL + 1))
        self.assertIsNone(ip.cache_key("", "acc1", 180))
        ip.cache_put(None, {"sampled": 1})

    def test_catalog_matches_frontend_16_areas(self):
        import pathlib
        import re
        src = (pathlib.Path(__file__).resolve().parents[2] / "frontend/lib/nucleo/lifeAreas.ts").read_text()
        block = src.split("LIFE_AREA_IDS = [", 1)[1].split("]", 1)[0]
        ids = set(re.findall(r'"([a-z]+)"', block))
        self.assertEqual(len(ids), 16)
        self.assertEqual(set(ic.CATEGORY_IDS), ids)
        self.assertEqual(ic.clean_exclude(["agenda"]), ["events"])

    def test_counts_match_labeled_sample(self):
        # Muestra verificable etiquetada a mano: (remitente, asunto, etiquetas, esperado).
        sample = [
            ("CFE <avisos@cfe.mx>", "Tu recibo de luz de octubre", [], "bills"),
            ("Telmex <facturas@telmex.com>", "Factura disponible", [], "bills"),
            ("BBVA <alertas@bbva.mx>", "Transferencia SPEI recibida", [], "money"),
            ("PayPal <service@paypal.com>", "Recibiste un pago", [], "money"),
            ("Amazon <envios@amazon.com.mx>", "Tu pedido fue enviado", [], "orders"),
            ("Mercado Libre <a@mercadolibre.com>", "Paquete entregado", [], "orders"),
            ("Netflix <info@netflix.com>", "Tu membresía se renovó", [], "subscriptions"),
            ("Google <no-reply@accounts.google.com>", "Alerta de seguridad", [], "security"),
            ("Banco <x@banco.mx>", "Tu código de verificación", [], "security"),
            ("Aeroméxico <r@aeromexico.com>", "Itinerario de tu vuelo", [], "travel"),
            ("Clínica <c@clinica.mx>", "Recordatorio de cita médica", [], "health"),
            ("GNP <p@gnp.com.mx>", "Tu póliza", [], "insurance"),
            ("SAT <n@sat.gob.mx>", "Buzón tributario SAT", [], "government"),
            ("Universidad <u@uni.mx>", "Inscripción al curso", [], "education"),
            ("Zoom <no-reply@zoom.us>", "Invitación a reunión", [], "events"),
            ("Cliente <c@empresa.mx>", "Cotización del proyecto", [], "work"),
            ("Condominio <adm@condo.mx>", "Cuota de mantenimiento", [], "home"),
            ("YouTube <noreply@youtube.com>", "Nuevo video", [], "social"),
            ("Tienda <n@tienda.mx>", "50% de descuento", [], "promos"),
            ("Boletín <n@boletin.mx>", "Novedades", ["HAS_LIST_HEADERS"], "promos"),
            ("Ana <ana@ejemplo.mx>", "hola", [], "other"),
            ("Papá <p@ejemplo.mx>", "fotos", ["CATEGORY_PERSONAL"], "other"),
        ]
        expected = {}
        for sender, subject, labels, cat in sample:
            self.assertEqual(ic.import_category(sender, subject, labels), cat, subject)
            expected[cat] = expected.get(cat, 0) + 1
        preview = ip.build_preview([(s, t, l) for s, t, l, _ in sample], len(sample))
        for cat in ic.CATEGORY_IDS:
            self.assertEqual(preview["categories"][cat], expected.get(cat, 0), cat)
        self.assertEqual(sum(preview["categories"].values()), len(sample))  # sin duplicar
        worlds = {"hogar": 0, "ocupacion": 0, "personal": 0}
        for sender, subject, labels, _ in sample:
            area = ic.v2_area(sender, subject, labels)
            if area != ic.REVIEW_ID:
                worlds[ic.V2_AREA_WORLD[area]] += 1
        self.assertEqual(preview["spheres"], worlds)
        self.assertEqual(preview["worlds"], worlds)
        self.assertEqual(sum(preview["areas"].values()) + preview["review"], len(sample))
        # Remitentes con 1 solo correo nunca salen como ejemplo.
        self.assertEqual(preview["examples"], {})


if __name__ == "__main__":
    unittest.main()
