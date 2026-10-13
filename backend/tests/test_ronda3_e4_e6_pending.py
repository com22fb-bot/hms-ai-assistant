"""Ronda 3 · E4–E6: especificaciones PENDIENTES (sin código de producto todavía).

Cada prueba documenta un criterio de aceptación aprobado por ASTRA y se marca
xfail(strict=True): cuando se implemente la etapa, la prueba debe pasar y
quitarse el marcador.
"""
import importlib

import pytest

PENDING = pytest.mark.xfail(strict=True, reason="E4–E6 no implementadas en ronda 3 (fuera de alcance)")


def _module(name):
    return importlib.import_module(name)


@PENDING
def test_e4_mail_index_guarda_list_unsubscribe_sin_cuerpo():
    mod = _module("app.services.mail_index")
    row = mod.index_row_from_headers({"From": "a@x.test", "List-Unsubscribe": "<mailto:u@x.test>"})
    assert row["is_bulk"] is True and "body" not in row


@PENDING
def test_e5_excluidos_no_descargan_cuerpo():
    mod = _module("app.services.mail_index")
    assert mod.should_fetch_body({"status": "excluded"}) is False


@PENDING
def test_e6_prioritario_no_anula_exclusion():
    mod = _module("app.services.priority_contacts")
    assert mod.should_alert(message={"excluded": True}, priority=True) is False


@PENDING
def test_e6_score_reciprocidad_supera_frecuencia():
    mod = _module("app.services.priority_contacts")
    a = mod.score(n_in=1288, n_out=0, threads=1260, is_bulk=True)
    b = mod.score(n_in=10, n_out=14, threads=18, is_bulk=False)
    assert b > a
