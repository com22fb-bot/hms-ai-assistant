"""Criterio 8 de ASTRA: los números del importador = mensajes únicos que realmente se procesan."""
import itertools

from app.services.import_categories import (PROTECTED_IDS, PROTECTED_PREFIX, REVIEW_ID, V2_AREA_IDS,
                                            download_plan, skip_message, summarize)

SENDERS = [
    ("Banco BBVA <alertas@bbva.mx>", "Cargo en tu tarjeta", ["INBOX"]),
    ("SAT <noreply@sat.gob.mx>", "Tu factura CFDI", ["INBOX"]),
    ("Google <no-reply@accounts.google.com>", "Alerta de seguridad: nuevo inicio de sesión", ["INBOX"]),
    ("CFE <facturacion@cfe.mx>", "Tu recibo de luz", ["INBOX"]),
    ("Hospital Ángeles <citas@hospitalangeles.com>", "Resultados de laboratorio", ["INBOX"]),
    ("Instagram <no-reply@mail.instagram.com>", "Tienes nuevos seguidores", ["CATEGORY_SOCIAL"]),
    ("Liverpool <promo@liverpool.com.mx>", "50% de descuento hoy", ["CATEGORY_PROMOTIONS"]),
    ("Ana <ana@example.com>", "Junta del lunes", ["INBOX"]),
    ("Escuela <avisos@colegio.edu.mx>", "Circular de padres", ["INBOX"]),
    ("Amazon <envios@amazon.com.mx>", "Tu pedido fue enviado", ["INBOX"]),
    ("desconocido@xyz.io", "hola", ["INBOX"]),
    ("Netflix <info@netflix.com>", "Nuevo en Netflix", ["CATEGORY_PROMOTIONS"]),
]
HEADERS = [h for h in SENDERS for _ in range(3)] + SENDERS[:5]


def processed(exclude):
    return sum(1 for s, subj, labels in HEADERS if not skip_message(exclude, s, subj, labels))


def test_areas_y_por_revisar_son_particion_sin_dobles_conteos():
    p = summarize(HEADERS)
    assert sum(p["areas"].values()) + p["review"] == p["sampled"] == len(HEADERS)
    assert sum(sum(c.values()) for c in p["area_protected"].values()) == sum(p["protected"].values())


def test_plan_coincide_con_lo_que_realmente_se_procesa():
    p = summarize(HEADERS)
    ids = [*V2_AREA_IDS, REVIEW_ID]
    choices = [[]] + [[a] for a in ids] + [list(c) for c in itertools.combinations(ids, 3)] + [ids]
    prot_off = [[], [PROTECTED_PREFIX + PROTECTED_IDS[0]], [PROTECTED_PREFIX + x for x in PROTECTED_IDS]]
    for areas_off in choices:
        for off in prot_off:
            exclude = areas_off + off
            plan = download_plan(p, exclude)
            assert plan["to_process"] == processed(exclude), exclude
            assert plan["total"] == len(HEADERS)
            assert plan["selected"] + plan["protected"] + plan["excluded"] == len(HEADERS)


def test_sin_exclusiones_todo_se_descarga():
    p = summarize(HEADERS)
    assert download_plan(p, []) == {"selected": len(HEADERS), "protected": 0, "excluded": 0,
                                    "to_process": len(HEADERS), "total": len(HEADERS)}


def test_paridad_con_frontend_importPlan_ts():
    p = summarize(HEADERS)
    assert download_plan(p, ["dinero"]) == {"selected": 29, "protected": 12, "excluded": 0, "to_process": 41, "total": 41}
    assert download_plan(p, ["dinero", "proteger:facturas"])["to_process"] == 33
    assert download_plan(p, ["revisar", "promociones"]) == {"selected": 25, "protected": 4, "excluded": 12, "to_process": 29, "total": 41}
