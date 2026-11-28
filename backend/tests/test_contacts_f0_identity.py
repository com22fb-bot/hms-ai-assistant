"""CONTACTS_V1 · F0 · Interfaz de identidad (contrato) — datos 100 % sintéticos, sin red."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import contact_identity as ci  # noqa: E402

H01_QUOTED = '"aviso@banamex.com.mx, Soporte" <x@atacante.test>'
H01_UNQUOTED = "aviso@banamex.com.mx, Soporte <x@atacante.test>"   # lo que escribe hoy _format_sender
H01_ENCODED = "=?utf-8?q?aviso=40banamex.com.mx=2C_Soporte?= <x@atacante.test>"
H01_REVERSED = "atacante@x.test, Soporte <aviso@banamex.com.mx>"


def sender(v):
    return ci.identity_from_stored_sender(v)


# ----------------------------------------------------------------- vector H01
def test_h01_entre_comillas_identidad_es_la_direccion_real():
    i = sender(H01_QUOTED)
    assert i.trusted and i.address_norm == "x@atacante.test"
    assert i.display_name == "aviso@banamex.com.mx, Soporte"     # se conserva como descriptivo
    assert "display_name_contains_address" in i.flags            # indicio de suplantación
    assert "banamex" not in i.address_norm


def test_h01_encoded_word_no_se_vuelve_segunda_direccion():
    i = ci.identity_from_header(H01_ENCODED, source="imap")
    assert i.trusted and i.address_norm == "x@atacante.test"
    assert "display_name_contains_address" in i.flags


@pytest.mark.parametrize("value", [H01_UNQUOTED, H01_REVERSED, "a@x.test, b@y.test"])
def test_h01_sin_comillas_o_multiple_es_ambiguo_y_sin_identidad(value):
    i = sender(value)
    assert i.parse_status == ci.PARSE_AMBIGUOUS and i.reason == "multiple"
    assert i.address_norm == "" and not i.trusted and i.domain == ""
    assert i.address_original == value                           # no se destruye el original


def test_forma_heredada_con_coma_se_acepta_via_sender_identity_con_bandera():
    """H01 (#218) acepta legacy_unquoted: un único buzón válido, el de los <...> finales."""
    i = sender("Perez, Juan <juan@ejemplo.test>")
    assert i.trusted and i.parse_status == ci.PARSE_OK and i.address_norm == "juan@ejemplo.test"
    assert "legacy_unquoted" in i.flags and i.display_name == "Perez, Juan"
    assert ci.sender_identity.parse_sender("Perez, Juan <juan@ejemplo.test>").status == "legacy_unquoted"


@pytest.mark.parametrize("value", [
    "Perez <a@b.test>, Juan <juan@ejemplo.test>",          # dos buzones: nunca el primero ni el último
    "Soporte: a@x.test <juan@x.test>",                     # sintaxis de grupo en el nombre
    "aviso@banamex.com.mx <x@atacante.test>",              # dirección sin comillas como nombre
    "atacante@x.test, Soporte <aviso@banamex.com.mx>",
    '"Grupo: a@x.test;" <b@y.test>, c@z.test',
])
def test_legacy_nunca_confia_en_la_primera_direccion(value):
    i = sender(value)
    assert not i.trusted and i.address_norm == ""
    assert i.parse_status in (ci.PARSE_AMBIGUOUS, ci.PARSE_INVALID)


# ------------------------------------------------------- nombre visible ≠ identidad
def test_nombre_visible_nunca_es_identidad_ni_criterio_de_fusion():
    a = sender('"Banco Seguro" <alertas@banco.test>')
    b = sender('"Banco Seguro" <alertas@phish.test>')
    c = sender('"alertas@banco.test" <otro@phish.test>')
    assert {a.address_norm, b.address_norm, c.address_norm} == {
        "alertas@banco.test", "alertas@phish.test", "otro@phish.test"}
    assert a.display_name == b.display_name  # mismo nombre, identidades distintas
    assert c.address_norm != a.address_norm and "display_name_contains_address" in c.flags


def test_solo_nombre_sin_direccion_es_invalido():
    for v in ["Soporte Banco", "juan", "<>", '"aviso@banamex.com.mx"']:
        i = sender(v)
        assert not i.trusted and i.address_norm == ""


# ------------------------------------------------------------- normalización
@pytest.mark.parametrize("raw,norm", [
    ("Juan.Perez+banco@GMail.com", "juanperez@gmail.com"),     # equivalencia de mail_direction
    ("juan.perez@googlemail.com", "juanperez@gmail.com"),
    ("Ana.Lopez+x@Empresa.MX", "ana.lopez+x@empresa.mx"),       # fuera de Gmail no se quitan puntos ni +
    ("x@München.de", "x@xn--mnchen-3ya.de"),                    # dominio IDNA
    ('"José" <JOSÉ@Ejemplo.MX>', "josé@ejemplo.mx"),            # RFC 6531
    ("Amazon.com <a@amazon.com>", "a@amazon.com"),              # defecto obsoleto benigno
])
def test_normaliza_sin_destruir_original(raw, norm):
    i = sender(raw)
    assert i.trusted and i.address_norm == norm
    assert i.address_original != "" and i.address_original.lower() != "" and "@" in i.address_original
    if raw.startswith("Juan.Perez"):
        assert i.address_original == "Juan.Perez+banco@GMail.com"


@pytest.mark.parametrize("raw,reason", [
    ("", "empty"),
    ("a@b@c.test", "no_address"),
    ("juan@localhost", "no_address"),
    ("juan@[10.0.0.1]", None),
    ("a@ejemplo.mx.", None),                                   # punto final: el analizador lo marca
    ("Juan <juan@x.test", "header_defects"),
    ("x@a.test\r\nBcc: y@b.test", "control_chars_or_too_long"),
    ("x@" + "a" * 1200 + ".test", "control_chars_or_too_long"),
])
def test_entradas_no_confiables(raw, reason):
    i = sender(raw)
    assert not i.trusted and i.address_norm == ""
    if reason:
        assert i.reason == reason


def test_lista_de_destinatarios_un_elemento_por_buzon():
    items = ci.identities_from_header_list('"Pérez, Juan" <juan@x.test>, ana@y.test, undisclosed-recipients:;',
                                           source="gmail_api")
    assert [i.address_norm for i in items] == ["juan@x.test", "ana@y.test"]
    assert items[0].display_name == "Pérez, Juan"


def test_lista_con_defectos_pone_en_revision_sin_inventar():
    items = ci.identities_from_header_list("Perez, Juan <juan@x.test>", source="imap")
    assert all(not i.trusted for i in items)


def test_estructurado_graph_y_jsonb():
    ok = ci.identity_from_structured("Ana@Y.test", "Ana, Ventas", source="microsoft_graph")
    assert ok.trusted and ok.address_norm == "ana@y.test" and ok.address_original == "Ana@Y.test"
    bad = ci.identity_from_structured(H01_UNQUOTED, "x", source="microsoft_graph")
    assert bad.parse_status == ci.PARSE_AMBIGUOUS and not bad.address_norm
    named = ci.identity_from_structured("Ana <ana@y.test>", None, source="stored_recipients")
    assert not named.trusted and named.reason == "not_bare_address"
    rows = ci.identities_from_structured_list(
        [{"name": "A", "email": "a@x.test"}, {"name": "B", "email": ""}, 42], source="stored_recipients")
    assert [r.parse_status for r in rows] == ["ok", "invalid", "invalid"]


def test_fuente_y_rol_desconocidos_fallan_explicitamente():
    with pytest.raises(ci.ContactIdentityError):
        ci.identity_from_header("a@x.test", source="adivinado")
    with pytest.raises(ci.ContactIdentityError):
        ci.identity_from_header("a@x.test", source="imap", role="nombre")


def test_contrato_serializable():
    c = sender(H01_QUOTED).as_contract()
    assert set(c) == {"address_original", "address_norm", "display_name", "parse_status", "source", "reason", "flags"}
    assert c["parse_status"] in ci.PARSE_STATUSES and c["source"] == "stored_sender"


# ------------------------------------------------- contrato con H01 (PR #218, ya en la rama)
CONTRACT_VECTORS = [
    H01_QUOTED, H01_UNQUOTED, H01_ENCODED, H01_REVERSED, "Perez, Juan <juan@ejemplo.test>",
    "Juan <juan@x.test>", "juan@x.test", "a@x.test, b@y.test", "Soporte", "", "<>", "a@b@c.test",
    '"José" <JOSÉ@Ejemplo.MX>', "Amazon.com <a@amazon.com>", "Juan <juan@x.test",
    "Perez <a@b.test>, Juan <juan@ejemplo.test>", "Soporte: a@x.test <juan@x.test>",
    '"Grupo: a@x.test;" <b@y.test>, c@z.test',
]


@pytest.mark.parametrize("value", CONTRACT_VECTORS)
def test_contrato_h01_f0_nunca_es_mas_permisivo_que_h01(value):
    """Si F0 confía en una dirección, H01 también y es la misma. F0 puede ser más estricto."""
    theirs = ci.sender_identity.parse_sender(value)
    mine = sender(value)
    if mine.trusted:
        assert theirs.trusted
        local, domain = theirs.email.rsplit("@", 1)
        assert mine.address_norm == ci.normalize_addr_spec(local, domain)[0]


def test_contrato_h01_vector_principal_coincide():
    stored = ci.sender_identity.canonical_sender(H01_QUOTED)   # lo que guarda el importador tras #218
    assert sender(stored).address_norm == "x@atacante.test"
    assert ci.sender_identity.parse_sender(stored).email == "x@atacante.test"


def test_h01_rechaza_lo_que_f0_aceptaria_por_su_cuenta(monkeypatch):
    """La autoridad sobre la cadena guardada es H01: si H01 no confía, F0 no confía."""
    monkeypatch.setattr(ci.sender_identity, "parse_sender",
                        lambda v: ci.sender_identity.SenderIdentity("", "", "multiple"))
    i = sender("Juan <juan@x.test>")
    assert not i.trusted and i.reason == "h01_untrusted"
