"""CONTACTS_V1 · F1 · Participantes, direcciones y alias con FakeSupabase (sintético, sin red)."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import contact_registry_service as svc  # noqa: E402
from app.services.contact_registry_repository import (  # noqa: E402
    ContactRegistryError,
    ContactRegistryRepository,
)
from tests.contacts_fakes import ContactsFakeSupabase  # noqa: E402
from tests.fake_supabase import UniqueViolation  # noqa: E402

WS, WS2 = "00000000-0000-4000-8000-0000000000a1", "00000000-0000-4000-8000-0000000000b2"
ACC_G = {"id": "acc-g", "workspace_id": WS, "provider": "google", "email": "usuario.sintetico@gmail.com"}
ACC_Y = {"id": "acc-y", "workspace_id": WS, "provider": "yahoo", "email": "usuario.sintetico@yahoo.test"}
ACC_OTHER = {"id": "acc-o", "workspace_id": WS2, "provider": "google", "email": "otra.persona@gmail.com"}
NEW_TABLES = {"message_participants", "contact_addresses", "own_address_aliases"}


def msg(mid, account, *, sender, to=(), cc=(), bcc=(), direction="inbound", at="2026-11-01T10:00:00+00:00"):
    return {"id": mid, "account_id": account["id"], "provider": account["provider"], "sender": sender,
            "recipients": [{"name": n, "email": e} for n, e in to], "cc": [{"name": n, "email": e} for n, e in cc],
            "bcc": [{"name": n, "email": e} for n, e in bcc], "direction": direction, "received_at": at}


@pytest.fixture()
def db():
    return ContactsFakeSupabase({"communication_accounts": [dict(ACC_G), dict(ACC_Y), dict(ACC_OTHER)]})


@pytest.fixture()
def on(monkeypatch):
    monkeypatch.setenv("CONTACTS_V1_ENABLED", "true")


def contacts(db, ws=WS):
    return sorted(r["address_norm"] for r in db.tables.get("contact_addresses", []) if r["workspace_id"] == ws)


def parts(db, mid):
    return sorted((r["role"], r["position"], r["address_norm"], r["parse_status"])
                  for r in db.tables.get("message_participants", []) if r["message_id"] == mid)


# ------------------------------------------------------------------ bandera
def test_bandera_apagada_por_defecto_no_toca_la_bd(db, monkeypatch):
    monkeypatch.delenv("CONTACTS_V1_ENABLED", raising=False)
    assert svc.contacts_v1_enabled() is False
    s = svc.ContactRegistryService(db)
    with pytest.raises(svc.ContactsV1Disabled):
        s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test"), ACC_G)
    for call in (lambda: s.list_contacts(WS), lambda: s.get_contact(WS, "a@x.test"),
                 lambda: s.decide_alias(WS, "a@x.test", "confirmed", None), lambda: s.list_participants(WS, "m1")):
        with pytest.raises(svc.ContactsV1Disabled):
            call()
    assert db.calls == []


@pytest.mark.parametrize("value", ["false", "0", "", "no", "off", "TRUE "])
def test_valores_de_bandera(monkeypatch, value):
    monkeypatch.setenv("CONTACTS_V1_ENABLED", value)
    assert svc.contacts_v1_enabled() is (value.strip().lower() == "true")


# -------------------------------------------------------- participantes
def test_recibido_crea_participantes_y_un_contacto_externo(db, on):
    s = svc.ContactRegistryService(db)
    out = s.record_message(WS, msg("m1", ACC_G, sender='"Ana Ruiz" <Ana.Ruiz@Cliente.test>',
                                   to=[("Usuario", "Usuario.Sintetico@gmail.com")], cc=[("Luis", "luis@cliente.test")]), ACC_G)
    assert parts(db, "m1") == [("cc", 0, "luis@cliente.test", "ok"), ("from", 0, "ana.ruiz@cliente.test", "ok"),
                               ("to", 0, "usuariosintetico@gmail.com", "ok")]
    own = [r for r in db.tables["message_participants"] if r["is_own"]]
    assert [r["role"] for r in own] == ["to"]                       # la cuenta conectada es propia
    assert contacts(db) == ["ana.ruiz@cliente.test", "luis@cliente.test"]  # nunca la propia
    frm = next(r for r in db.tables["message_participants"] if r["role"] == "from")
    assert frm["address_original"] == "Ana.Ruiz@Cliente.test" and frm["display_name"] == "Ana Ruiz"
    assert frm["source"] == "stored_sender" and frm["provider"] == "google" and frm["direction"] == "inbound"
    assert out["contacts_created"] == 2 and out["own"] == 1 and out["untrusted"] == 0


def test_idempotente_reprocesar_no_duplica_ni_escribe(db, on):
    s = svc.ContactRegistryService(db)
    m = msg("m1", ACC_G, sender="ana@cliente.test", to=[("", "usuario.sintetico@gmail.com"), ("", "b@x.test")])
    first = s.record_message(WS, m, ACC_G)
    snapshot = {t: [dict(r) for r in db.tables.get(t, [])] for t in NEW_TABLES}
    writes_before = len(db.writes())
    second = s.record_message(WS, m, ACC_G)
    assert first["inserted"] == 3 and second == {**second, "inserted": 0, "deleted": 0, "unchanged": 3,
                                                  "contacts_created": 0}
    assert len(db.writes()) == writes_before                       # cero escrituras la segunda vez
    assert {t: db.tables.get(t, []) for t in NEW_TABLES} == snapshot


def test_cambio_de_participantes_reemplaza_sin_restos(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test", to=[("", "a@x.test"), ("", "b@x.test")]), ACC_G)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test", to=[("", "b@x.test")]), ACC_G)
    assert parts(db, "m1") == [("from", 0, "ana@cliente.test", "ok"), ("to", 0, "b@x.test", "ok")]


def test_duplicados_en_el_mismo_rol_se_controlan(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test",
                             to=[("A", "Luis@X.test"), ("B", "luis@x.test")], cc=[("", "luis@x.test")]), ACC_G)
    assert parts(db, "m1") == [("cc", 0, "luis@x.test", "ok"), ("from", 0, "ana@cliente.test", "ok"),
                               ("to", 0, "luis@x.test", "ok")]
    assert contacts(db) == ["ana@cliente.test", "luis@x.test"]


def test_consolida_por_workspace_varias_cuentas_y_equivalencia_gmail(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="Juan.Perez+banco@GMail.com"), ACC_G)
    s.record_message(WS, msg("m2", ACC_Y, sender="juanperez@gmail.com"), ACC_Y)
    assert contacts(db) == ["juanperez@gmail.com"]                 # un solo contacto
    assert s.get_contact(WS, "Juan.Perez@gmail.com")["address_norm"] == "juanperez@gmail.com"
    origin = {r["account_id"]: r["address_original"] for r in db.tables["message_participants"]}
    assert origin == {"acc-g": "Juan.Perez+banco@GMail.com", "acc-y": "juanperez@gmail.com"}  # origen intacto


def test_aislamiento_entre_workspaces(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test"), ACC_G)
    s.record_message(WS2, msg("m9", ACC_OTHER, sender="ana@cliente.test"), ACC_OTHER)
    assert contacts(db, WS) == ["ana@cliente.test"] and contacts(db, WS2) == ["ana@cliente.test"]
    ids = {r["workspace_id"]: r["id"] for r in db.tables["contact_addresses"]}
    assert ids[WS] != ids[WS2]
    assert [r["workspace_id"] for r in s.list_contacts(WS)] == [WS]
    assert s.list_participants(WS, "m9") == []                    # mensaje de otro workspace: invisible


def test_cuenta_de_otro_workspace_se_rechaza_sin_escribir(db, on):
    s = svc.ContactRegistryService(db)
    with pytest.raises(ContactRegistryError):
        s.record_message(WS, msg("m9", ACC_OTHER, sender="ana@cliente.test"), ACC_OTHER)
    with pytest.raises(ContactRegistryError):
        s.record_message(WS, msg("m9", ACC_G, sender="ana@cliente.test"), ACC_Y)   # mensaje de otra cuenta
    assert db.writes() == []


# ------------------------------------------------------- H01 y ambigüedad
def test_h01_sin_comillas_no_crea_contacto_ni_identidad_falsa(db, on):
    s = svc.ContactRegistryService(db)
    out = s.record_message(WS, msg("m1", ACC_G, sender="aviso@banamex.com.mx, Soporte <x@atacante.test>"), ACC_G)
    row = db.tables["message_participants"][0]
    assert row["parse_status"] == "ambiguous" and row["address_norm"] is None and row["parse_reason"] == "multiple"
    assert row["address_original"] == "aviso@banamex.com.mx, Soporte <x@atacante.test>"
    assert contacts(db) == [] and out["untrusted"] == 1


def test_h01_con_comillas_identidad_real_y_nombre_descriptivo(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender='"aviso@banamex.com.mx, Soporte" <x@atacante.test>'), ACC_G)
    row = db.tables["message_participants"][0]
    assert row["address_norm"] == "x@atacante.test" and row["display_name"] == "aviso@banamex.com.mx, Soporte"
    assert row["flags"] == ["display_name_contains_address"]
    assert contacts(db) == ["x@atacante.test"]                     # jamás aviso@banamex.com.mx


def test_mismo_nombre_visible_no_fusiona(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender='"Banco" <alertas@banco.test>'), ACC_G)
    s.record_message(WS, msg("m2", ACC_G, sender='"Banco" <alertas@phish.test>'), ACC_G)
    assert contacts(db) == ["alertas@banco.test", "alertas@phish.test"]


def test_destinatario_malformado_queda_invalido_y_sin_contacto(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test",
                             to=[("Sin dirección", ""), ("x", "Ana <a@x.test>"), ("", "no-es-correo")]), ACC_G)
    assert [p[3] for p in parts(db, "m1") if p[0] == "to"] == ["invalid", "ambiguous", "invalid"]
    assert contacts(db) == ["ana@cliente.test"]


# ---------------------------------------------------------------- alias
def test_alias_de_enviado_se_detecta_no_es_propio_ni_contacto(db, on):
    s = svc.ContactRegistryService(db)
    out = s.record_message(WS, msg("s1", ACC_G, sender="Usuario <yo@alias-propio.test>",
                                   to=[("", "ana@cliente.test")], direction="outbound"), ACC_G)
    alias = db.tables["own_address_aliases"][0]
    assert alias["address_norm"] == "yo@alias-propio.test" and alias["status"] == "detected"
    assert alias["evidence"]["reason"] == "from_of_outbound"
    assert contacts(db) == ["ana@cliente.test"] and out["aliases_detected"] == 1
    assert s.classify_address(WS, "yo@alias-propio.test") == svc.CLASS_DETECTED_ALIAS
    assert not s.own_address_book(WS).is_own("yo@alias-propio.test")


def test_alias_confirmado_es_propio_rechazado_es_externo_y_reversible(db, on):
    s = svc.ContactRegistryService(db)
    m = msg("s1", ACC_G, sender="yo@alias-propio.test", to=[("", "ana@cliente.test")], direction="outbound")
    s.record_message(WS, m, ACC_G)
    s.decide_alias(WS, "yo@alias-propio.test", "confirmed", None)
    s.record_message(WS, m, ACC_G)
    frm = next(r for r in db.tables["message_participants"] if r["role"] == "from")
    assert frm["is_own"] is True and s.classify_address(WS, "yo@alias-propio.test") == svc.CLASS_CONFIRMED_ALIAS
    assert "yo@alias-propio.test" not in contacts(db)
    s.decide_alias(WS, "yo@alias-propio.test", "rejected", None)   # el usuario cambia de opinión
    s.record_message(WS, m, ACC_G)
    frm = next(r for r in db.tables["message_participants"] if r["role"] == "from")
    assert frm["is_own"] is False and s.classify_address(WS, "yo@alias-propio.test") == svc.CLASS_REJECTED_ALIAS
    assert "yo@alias-propio.test" in contacts(db)                 # rechazado = dirección externa


def test_deteccion_no_pisa_una_decision(db, on):
    repo = ContactRegistryRepository(db)
    repo.decide_alias(WS, "yo@alias-propio.test", "rejected", None)
    row, created = repo.record_detected_alias(WS, "yo@alias-propio.test", {"reason": "from_of_outbound"})
    assert not created and row["status"] == "rejected"
    with pytest.raises(ContactRegistryError):
        repo.decide_alias(WS, "yo@alias-propio.test", "detected", None)


def test_un_buzon_conectado_no_puede_ser_alias(db, on):
    s = svc.ContactRegistryService(db)
    with pytest.raises(ContactRegistryError):
        s.decide_alias(WS, "usuariosintetico@gmail.com", "confirmed", None)
    assert s.classify_address(WS, "usuariosintetico@gmail.com") == svc.CLASS_CONNECTED


@pytest.mark.parametrize("variant", ["Usuario.Sintetico+alias@GMail.com", "usuario.sintetico@googlemail.com",
                                     " USUARIOSINTETICO@gmail.com "])
def test_variante_gmail_de_un_buzon_conectado_no_puede_ser_alias(db, on, variant):
    """Bugbot #219: la guarda compara la forma canónica, no la cadena escrita."""
    s = svc.ContactRegistryService(db)
    assert s.classify_address(WS, variant) == svc.CLASS_CONNECTED
    with pytest.raises(ContactRegistryError):
        s.decide_alias(WS, variant, "confirmed", None)
    assert db.writes() == []


def test_repositorio_rechaza_formas_no_canonicas(db):
    repo = ContactRegistryRepository(db)
    for value in ("usuario.sintetico@gmail.com", "a+b@gmail.com", "a@googlemail.com", "x@münchen.de"):
        with pytest.raises(ContactRegistryError):
            repo.decide_alias(WS, value, "confirmed", None)
        with pytest.raises(ContactRegistryError):
            repo.record_detected_alias(WS, value, {})
        with pytest.raises(ContactRegistryError):
            repo.ensure_contact_address(WS, value, value)
    assert db.writes() == []


def test_alias_escrito_por_el_usuario_se_guarda_canonizado(db, on):
    s = svc.ContactRegistryService(db)
    row = s.decide_alias(WS, "Yo.Mismo+trabajo@GMail.com", "confirmed", None)
    assert row["address_norm"] == "yomismo@gmail.com"
    assert s.own_address_book(WS).is_own("yomismo@gmail.com")


def test_enviado_desde_la_cuenta_conectada_no_genera_alias(db, on):
    s = svc.ContactRegistryService(db)
    out = s.record_message(WS, msg("s1", ACC_G, sender="Usuario.Sintetico@gmail.com", to=[("", "ana@cliente.test")],
                                   direction="outbound"), ACC_G)
    assert out["aliases_detected"] == 0 and db.tables.get("own_address_aliases", []) == []


# -------------------------------------------------- límites de F1 y repositorio
def test_f1_no_escribe_estadisticas_ni_tablas_existentes(db, on):
    s = svc.ContactRegistryService(db)
    s.record_message(WS, msg("m1", ACC_G, sender="ana@cliente.test", to=[("", "usuario.sintetico@gmail.com")]), ACC_G)
    assert {c[0] for c in db.writes()} <= NEW_TABLES               # nada en communication_*, casos, etc.
    inserted = [c[2] for c in db.writes("contact_addresses")]
    assert inserted == [{"workspace_id": WS, "address_norm": "ana@cliente.test", "originals": ["ana@cliente.test"]}]
    assert not any(hasattr(ContactRegistryRepository, n) for n in ("refresh_stats", "update_stats", "set_counts"))


def test_repositorio_valida_antes_de_escribir(db):
    repo = ContactRegistryRepository(db)
    base = {"message_id": "m1", "workspace_id": WS, "account_id": "acc-g", "role": "from", "position": 0,
            "address_original": "x", "display_name": None, "parse_reason": "ok", "source": "fixture",
            "provider": None, "direction": "inbound", "occurred_at": "2026-11-01T10:00:00+00:00", "flags": []}
    bad = [
        {**base, "parse_status": "ok", "address_norm": "Ana@X.test", "is_own": False},
        {**base, "parse_status": "ambiguous", "address_norm": "a@x.test", "is_own": False},
        {**base, "parse_status": "invalid", "address_norm": None, "is_own": True},
        {**base, "parse_status": "raro", "address_norm": None, "is_own": False},
        {**base, "workspace_id": WS2, "parse_status": "ok", "address_norm": "a@x.test", "is_own": False},
    ]
    for row in bad:
        with pytest.raises(ContactRegistryError):
            repo.replace_message_participants(WS, "m1", [row])
    with pytest.raises(ContactRegistryError):
        repo.ensure_contact_address(WS, "sin-arroba", "sin-arroba")
    assert db.writes() == []


def test_carrera_en_alta_de_contacto_devuelve_la_existente(db):
    repo = ContactRegistryRepository(db)
    real_get = repo.get_contact_address
    calls = {"n": 0}

    def get_once_missing(ws, norm):
        calls["n"] += 1
        if calls["n"] == 1:
            db.tables.setdefault("contact_addresses", []).append(
                {"id": "otro-proceso", "workspace_id": ws, "address_norm": norm, "originals": []})
            return None
        return real_get(ws, norm)

    repo.get_contact_address = get_once_missing
    row, created = repo.ensure_contact_address(WS, "ana@cliente.test", "Ana@Cliente.test")
    assert not created and row["id"] == "otro-proceso" and len(db.tables["contact_addresses"]) == 1


def test_carrera_en_decision_de_alias_actualiza_la_existente(db):
    repo = ContactRegistryRepository(db)
    real_get = repo.get_alias
    calls = {"n": 0}

    def get_once_missing(ws, norm):
        calls["n"] += 1
        if calls["n"] == 1:
            db.tables.setdefault("own_address_aliases", []).append(
                {"id": "otro-proceso", "workspace_id": ws, "address_norm": norm, "status": "detected", "evidence": {}})
            return None
        return real_get(ws, norm)

    repo.get_alias = get_once_missing
    row = repo.decide_alias(WS, "yo@alias-propio.test", "confirmed", "usuario-1")
    assert row["status"] == "confirmed" and len(db.tables["own_address_aliases"]) == 1
    assert db.tables["own_address_aliases"][0]["status"] == "confirmed"


def test_fake_aplica_unicidad_de_la_migracion(db):
    db.table("contact_addresses").insert({"workspace_id": WS, "address_norm": "a@x.test"}).execute()
    with pytest.raises(UniqueViolation):
        db.table("contact_addresses").insert({"workspace_id": WS, "address_norm": "a@x.test"}).execute()


def test_mensaje_sin_fecha_o_direccion_desconocida_falla_cerrado(db, on):
    s = svc.ContactRegistryService(db)
    m = msg("m1", ACC_G, sender="ana@cliente.test")
    m["received_at"] = None
    with pytest.raises(ContactRegistryError):
        s.record_message(WS, m, ACC_G)
    with pytest.raises(ContactRegistryError):
        s.record_message(WS, {**msg("m2", ACC_G, sender="ana@cliente.test"), "direction": "lateral"}, ACC_G)
    assert db.writes() == []
