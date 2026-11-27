"""H01 (auditoría forense de ingesta 2026-11-27): identidad canónica del remitente.

Pruebas sintéticas, deterministas, sin red y sin base de datos real (FakeSupabase en
memoria). Dominios ficticios (*.test) salvo ``banamex.com.mx``, que es un dominio del
catálogo interno de remitentes; ningún correo real.

Bloques del prompt de corrección: A (comas), B (vector H01/H02), C (nombres
legítimos), D (anómalos), E (Gmail API), F (Microsoft Graph), G (IMAP), H
(consumidores). La regresión funcional (I) es la suite existente.
"""
from __future__ import annotations

import email
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")

from app.services import gmail_full_sync, microsoft_import, yahoo_import
from app.services.case_engine import _sender_parts as case_sender_parts
from app.services.classification_catalog import identify_sender
from app.services.classification_catalog.matching import sender_domain, sender_email
from app.services.gmail_sync import _format_sender
from app.services.import_categories import sender_domain as categories_sender_domain
from app.services.mail_direction import normalize_address, own_address_set
from app.services.mail_insights import _sender_parts as insights_sender_parts
from app.services.message_rules_service import _sender_domain as rules_sender_domain
from app.services.message_rules_service import _sender_email as rules_sender_email
from app.services.message_watch_service import _sender_email as watch_sender_email
from app.services.microsoft_import import graph_address
from app.services.safe_case_classifier import classify_message
from app.services.sender_identity import canonical_sender, format_sender, parse_sender
from tests.fake_supabase import FakeSupabase

BANK = "banamex.com.mx"
INJECTED_NAME = f"aviso@{BANK}, Soporte"
REAL = "x@atacante.test"
BODY = "Tiene un pago pendiente, favor de pagar antes del viernes."


def _all_consumers(stored: str) -> dict:
    return {
        "sender_email": sender_email(stored),
        "sender_domain": sender_domain(stored),
        "case_engine._sender_parts": case_sender_parts(stored)[1],
        "mail_insights._sender_parts": insights_sender_parts(stored)[1],
        "mail_insights.domain": insights_sender_parts(stored)[2],
        "import_categories.sender_domain": categories_sender_domain(stored),
        "message_rules._sender_email": rules_sender_email(stored),
        "message_rules._sender_domain": rules_sender_domain(stored),
        "message_watch._sender_email": watch_sender_email(stored),
        "mail_direction.normalize_address": normalize_address(stored),
    }


def _assert_identity(stored: str, email_value: str) -> None:
    domain = email_value.rsplit("@", 1)[1] if email_value else ""
    got = _all_consumers(stored)
    for key, value in got.items():
        expected = domain if "domain" in key else email_value
        assert value in (expected, None if not expected else expected), (key, stored, got)
        if not expected:
            assert not value, (key, stored, got)


def _msg(sender: str, body: str = BODY) -> dict:
    return {"sender": sender, "subject": "Aviso", "body_text": body, "labels": ["INBOX"],
            "direction": "inbound", "is_unread": True}


# ---------------------------------------------------------------- A. comas
@pytest.mark.parametrize(
    "raw, email_value, name",
    [
        ("Perez, Juan <j@example.test>", "j@example.test", "Perez, Juan"),
        ('"Perez, Juan" <j@example.test>', "j@example.test", "Perez, Juan"),
        (f'"{INJECTED_NAME}" <{REAL}>', REAL, INJECTED_NAME),
    ],
)
def test_a_names_with_commas_keep_real_address(raw, email_value, name):
    stored = _format_sender(raw)
    identity = parse_sender(stored)
    assert identity.email == email_value
    assert identity.display_name == name
    _assert_identity(stored, email_value)
    assert BANK not in sender_domain(stored)


# ------------------------------------------------- B/E/F/G. recorrido real por proveedor
class _GmailService:
    """Subconjunto de googleapiclient: users().messages().list/get().execute()."""

    def __init__(self, messages: list[dict]):
        self._messages = {m["id"]: m for m in messages}
        self._op = None

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, **_kwargs):
        self._op = ("list", None)
        return self

    def get(self, **kwargs):
        self._op = ("get", kwargs.get("id"))
        return self

    def execute(self):
        kind, ident = self._op
        if kind == "list":
            return {"messages": [{"id": key} for key in self._messages]}
        return self._messages[ident]


def _gmail_raw(from_header: str, message_id: str = "m1") -> dict:
    return {
        "id": message_id,
        "threadId": f"t-{message_id}",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": BODY,
        "internalDate": "1764000000000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": from_header},
                {"name": "To", "value": "Yo <yo@example.test>"},
                {"name": "Subject", "value": "Aviso"},
                {"name": "Message-ID", "value": f"<{message_id}@example.test>"},
            ],
            "body": {"data": "VGllbmUgdW4gcGFnbyBwZW5kaWVudGUu"},
        },
    }


def _storage(db: FakeSupabase, account: dict) -> SimpleNamespace:
    return SimpleNamespace(client=db, get_account=lambda _id: account)


def run_gmail(from_headers: list[str]) -> list[str]:
    db = FakeSupabase({"communication_threads": [], "communication_messages": []})
    account = {"id": "acc-g", "email": "yo@example.test", "provider": "google"}
    service = _GmailService([_gmail_raw(h, f"m{i}") for i, h in enumerate(from_headers)])
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(gmail_full_sync, "OAuthStorage", lambda: _storage(db, account)))
        stack.enter_context(mock.patch.object(gmail_full_sync, "build", lambda *a, **k: service))
        result = gmail_full_sync.sync_gmail_page(credentials=None, account_id="acc-g")
    assert result["errors"] == 0, result
    return [row["sender"] for row in db.tables["communication_messages"]]


def run_graph(entries: list[dict]) -> list[str]:
    db = FakeSupabase({"communication_threads": [], "communication_messages": []})
    account = {"id": "acc-m", "email": "yo@example.test", "provider": "microsoft"}
    payloads = {f"id{i}": entry for i, entry in enumerate(entries)}

    def fake_get(_account, url, params=None):
        message_id = url.rsplit("/", 1)[1]
        return {
            "id": message_id,
            "subject": "Aviso",
            "from": payloads[message_id],
            "toRecipients": [{"emailAddress": {"name": "Yo", "address": "yo@example.test"}}],
            "receivedDateTime": "2026-11-27T12:00:00Z",
            "body": {"contentType": "text", "content": BODY},
            "conversationId": f"conv-{message_id}",
            "isRead": False,
            "hasAttachments": False,
            "internetMessageId": f"<{message_id}@example.test>",
        }

    refs = [microsoft_import.encode_microsoft_ref("inbox", key) for key in payloads]
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(microsoft_import, "OAuthStorage", lambda: _storage(db, account)))
        stack.enter_context(mock.patch.object(microsoft_import, "_graph_get_with_refresh", fake_get))
        result = microsoft_import.sync_microsoft_page(account=account, refs=refs, offset=0)
    assert result["errors"] == 0, result
    return [row["sender"] for row in db.tables["communication_messages"]]


class _ImapClient:
    def __init__(self, raw_by_uid: dict[str, bytes]):
        self.raw_by_uid = raw_by_uid

    def logout(self):
        return None


def run_imap(raw_from_headers: list[bytes], provider: str = "yahoo") -> list[str]:
    db = FakeSupabase({"communication_threads": [], "communication_messages": []})
    account = {"id": "acc-y", "email": f"yo@{provider}.example.test", "provider": provider}
    raws = {
        str(i + 1): b"From: " + header + b"\r\nTo: yo@example.test\r\nSubject: Aviso\r\n"
        b"Date: Fri, 27 Nov 2026 12:00:00 -0600\r\nMessage-ID: <m" + str(i).encode() + b"@example.test>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n" + BODY.encode()
        for i, header in enumerate(raw_from_headers)
    }
    client = _ImapClient(raws)

    def fetch_batch(_client, uids):
        return {uid: (email.message_from_bytes(raws[uid]), "") for uid in uids}

    refs = [yahoo_import.encode_yahoo_ref("INBOX", uid) for uid in raws]
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(yahoo_import, "OAuthStorage", lambda: _storage(db, account)))
        stack.enter_context(mock.patch.object(yahoo_import, "_prepare_imap_secret", lambda a, p, **k: (a, p)))
        stack.enter_context(mock.patch.object(yahoo_import, "_open_mailbox_client", lambda *a, **k: client))
        stack.enter_context(mock.patch.object(yahoo_import, "_select_folder", lambda *a, **k: None))
        stack.enter_context(mock.patch.object(yahoo_import, "_fetch_uid_batch", fetch_batch))
        result = yahoo_import.sync_yahoo_page(
            account=account, app_password="synthetic-not-a-secret", refs=refs, offset=0,
            mailbox_provider=provider,
        )
    assert result["errors"] == 0, result
    return [row["sender"] for row in db.tables["communication_messages"]]


def _assert_vector_neutralized(stored: str) -> None:
    identity = parse_sender(stored)
    assert identity.email == REAL, stored
    assert identity.domain == "atacante.test"
    _assert_identity(stored, REAL)
    assert identify_sender(stored) is None, stored
    # Mismo resultado que un remitente cualquiera del dominio del atacante: la
    # clasificación que quede depende solo del contenido, sin la marca del banco.
    verdict = classify_message(_msg(stored), existing_case=None)
    control = classify_message(_msg(f"Soporte <{REAL}>"), existing_case=None)
    assert verdict == control, (verdict, control)
    assert "banamex" not in verdict[2].lower()


def test_b_e_gmail_injection_vector_end_to_end():
    stored = run_gmail([f'"{INJECTED_NAME}" <{REAL}>'])
    assert stored == [f'"{INJECTED_NAME}" <{REAL}>']
    _assert_vector_neutralized(stored[0])


def test_b_f_graph_injection_vector_end_to_end():
    stored = run_graph([{"emailAddress": {"name": INJECTED_NAME, "address": REAL}}])
    assert stored == [f'"{INJECTED_NAME}" <{REAL}>']
    _assert_vector_neutralized(stored[0])


@pytest.mark.parametrize("provider", ["yahoo", "icloud"])
@pytest.mark.parametrize(
    "header",
    [
        b"=?utf-8?q?aviso@banamex.com.mx=2C_Soporte?= <x@atacante.test>",  # Q
        b"=?utf-8?b?YXZpc29AYmFuYW1leC5jb20ubXgsIFNvcG9ydGU=?= <x@atacante.test>",  # B
        b'"aviso@banamex.com.mx, Soporte" <x@atacante.test>',  # comillas
    ],
)
def test_b_g_imap_injection_vector_end_to_end(provider, header):
    stored = run_imap([header], provider=provider)
    assert stored == [f'"{INJECTED_NAME}" <{REAL}>']
    _assert_vector_neutralized(stored[0])


def test_b_legacy_rows_from_previous_serializer_are_not_attributed():
    # Fila guardada por el serializador anterior (Gmail con nombre entre comillas).
    legacy = f"{INJECTED_NAME} <{REAL}>"
    _assert_vector_neutralized(legacy)


def test_b_brand_still_detected_for_real_bank_address():
    for stored in (
        f"Citibanamex <alertas@{BANK}>",
        f'"Banamex, Alertas" <alertas@{BANK}>',
        f"Banamex, Alertas <alertas@{BANK}>",  # fila antigua sin comillas
        f"alertas@{BANK}",
    ):
        identity = identify_sender(stored)
        assert identity is not None and identity["domain"] == BANK, stored
        assert identity["email"] == f"alertas@{BANK}"


# --------------------------------------------------------- C. nombres legítimos
LEGIT = [
    ("Pérez, Juan", "j@example.test"),
    ("José Ñúñez", "jose@example.test"),
    ("東京 太郎", "taro@example.test"),
    ('Ana "La Jefa" Ruiz', "ana@example.test"),
    ("O'Brien", "ob@example.test"),
    ("Soporte (MX)", "soporte@example.test"),
    ("Nombre " * 30 + "Largo", "largo@example.test"),
    ("contacto@otro.test", "real@example.test"),
    ("Ventas <ventas@otro.test>", "real2@example.test"),
    ("a\\b; c: d", "special@example.test"),
]


@pytest.mark.parametrize("name, address", LEGIT)
def test_c_legitimate_names_round_trip_all_providers(name, address):
    expected_name = " ".join(name.split())
    graph = graph_address({"emailAddress": {"name": name, "address": address}})
    gmail = _format_sender(format_sender(name, address))
    for stored in (graph, gmail, _format_sender(graph)):
        identity = parse_sender(stored)
        assert identity.email == address, (stored, identity)
        assert identity.display_name == expected_name, (stored, identity)
        _assert_identity(stored, address)


@pytest.mark.parametrize(
    "raw, address, name",
    [
        ("josé@banco.example", "josé@banco.example", ""),  # RFC 6531 (Bugbot #218)
        ("Nombre <josé@banco.example>", "josé@banco.example", "Nombre"),
        ('"José, Ana" <josé@banco.example>', "josé@banco.example", "José, Ana"),
        ("Amazon.com <ship@amazon.example>", "ship@amazon.example", "Amazon.com"),  # punto en el nombre
        ("Dr. Juan Pérez <j@example.test>", "j@example.test", "Dr. Juan Pérez"),
        ("j@bañco.example", "j@bañco.example", ""),
    ],
)
def test_c_benign_defects_keep_single_address(raw, address, name):
    identity = parse_sender(raw)
    assert identity.status == "ok", identity
    assert (identity.email, identity.display_name) == (address, name)
    stored = canonical_sender(raw)
    assert parse_sender(stored).email == address, stored
    assert parse_sender(stored).display_name == name, stored
    _assert_identity(stored, address.lower())


def test_c_rfc2047_names_decoded_after_parsing():
    raw = "=?utf-8?q?P=C3=A9rez=2C_Juan?= <j@example.test>"
    stored = canonical_sender(raw)
    assert stored == '"Pérez, Juan" <j@example.test>'
    assert parse_sender(stored).email == "j@example.test"
    quoted_ew = '"=?utf-8?q?P=C3=A9rez=2C_Juan?=" <j@example.test>'
    assert parse_sender(_format_sender(quoted_ew)).email == "j@example.test"


def test_g_imap_legit_names_end_to_end():
    stored = run_imap([
        b"=?utf-8?q?P=C3=A9rez=2C_Juan?= <j@example.test>",
        b"=?utf-8?b?UMOpcmV6LCBKdWFu?= <j2@example.test>",
        b'"Perez, Juan" <j3@example.test>',
        "José Pérez <j4@example.test>".encode(),  # 8 bits sin codificar
        "Pérez, Juan <j5@example.test>".encode(),  # 8 bits, coma sin comillas
    ])
    assert [parse_sender(s).email for s in stored] == [
        "j@example.test", "j2@example.test", "j3@example.test", "j4@example.test", "j5@example.test",
    ]
    assert parse_sender(stored[0]).display_name == "Pérez, Juan"


def test_e_gmail_legit_names_end_to_end():
    stored = run_gmail([
        '"Perez, Juan" <j@example.test>',
        "Perez, Juan <j2@example.test>",
        "José Pérez <j3@example.test>",
        "j4@example.test",
    ])
    assert [parse_sender(s).email for s in stored] == [
        "j@example.test", "j2@example.test", "j3@example.test", "j4@example.test",
    ]


def test_f_graph_legit_names_end_to_end():
    stored = run_graph([
        {"emailAddress": {"name": "Perez, Juan", "address": "j@example.test"}},
        {"emailAddress": {"name": "", "address": "j2@example.test"}},
        {"emailAddress": {"name": "Ana", "address": "ana@example.test"}},
    ])
    assert stored == ['"Perez, Juan" <j@example.test>', "j2@example.test", "Ana <ana@example.test>"]


# ----------------------------------------------- D. múltiples direcciones y anómalos
@pytest.mark.parametrize(
    "raw",
    [
        "a@example.test, b@example.test",  # dos direcciones
        "A <a@example.test>, B <b@example.test>",
        f"Soporte <{REAL}>, aviso@{BANK}",
        "",  # vacío
        "   ",
        "Juan Pérez",  # nombre sin dirección
        "bad@@example.test",  # dirección malformada
        "Juan <>",
        '"x" <aviso@banamex.com.mx',  # incompleto
        f"Soporte <{REAL}> extra",
        "=?utf-8?q?aviso@banamex.com.mx?=",  # encoded-word que decodifica a una dirección
        f'"aviso@{BANK}"',
    ],
)
def test_d_anomalous_fields_never_invent_identity(raw):
    identity = parse_sender(raw)
    assert identity.email == "" and not identity.trusted, identity
    stored = canonical_sender(raw)
    assert parse_sender(stored).email == "", stored  # lo guardado tampoco fabrica una dirección
    _assert_identity(stored, "")
    assert identify_sender(stored) is None
    assert identify_sender(raw) is None


def test_d_address_without_name_and_malformed_encoded_word():
    assert parse_sender("<j@example.test>").email == "j@example.test"
    assert parse_sender("j@example.test").email == "j@example.test"
    broken = parse_sender("=?utf-8?q?bro ken <j@example.test>")
    assert broken.email == "j@example.test"


def test_d_imap_and_graph_anomalous_end_to_end():
    stored = run_imap([b"a@example.test, b@example.test", b"Solo Nombre"])
    assert all(parse_sender(s).email == "" for s in stored), stored
    graph = run_graph([{"emailAddress": {"name": f"aviso@{BANK}", "address": ""}}])
    assert parse_sender(graph[0]).email == "" and identify_sender(graph[0]) is None, graph


# -------------------------------------------------------- H. consumidores
def test_h_mail_direction_own_address_not_fabricated_from_name():
    own = own_address_set(["yo@example.test"])
    spoof = format_sender("yo@example.test, Soporte", REAL)
    assert normalize_address(spoof) == REAL
    assert normalize_address(spoof) not in own
    legacy_spoof = f"yo@example.test, Soporte <{REAL}>"
    assert normalize_address(legacy_spoof) not in own
    assert normalize_address("Yo <yo@example.test>") in own
    assert normalize_address("yo@example.test") in own


def test_h_classifier_own_address_rule_uses_real_address():
    own = {"yo@example.test"}
    spoof = format_sender("yo@example.test, Soporte", REAL)
    real_own = classify_message(_msg("Yo <yo@example.test>", "Hola"), existing_case=None, own_addresses=own)
    control = classify_message(_msg(f"Soporte <{REAL}>", "Hola"), existing_case=None, own_addresses=own)
    assert "propia" in real_own[2].lower()
    for stored in (spoof, f"yo@example.test, Soporte <{REAL}>"):
        verdict = classify_message(_msg(stored, "Hola"), existing_case=None, own_addresses=own)
        assert verdict == control, (stored, verdict)
        assert "propia" not in verdict[2].lower()


def test_h_case_engine_sender_parts_keeps_name_and_address():
    assert case_sender_parts('"Perez, Juan" <j@example.test>') == ("Perez, Juan", "j@example.test")
    assert case_sender_parts("Perez, Juan <j@example.test>") == ("Perez, Juan", "j@example.test")
    assert case_sender_parts("a@example.test, b@example.test")[1] is None
    assert case_sender_parts("") == (None, None)


def test_h_idempotent_canonical_form():
    for raw in ['"Perez, Juan" <j@example.test>', f'"{INJECTED_NAME}" <{REAL}>', "José <j@example.test>"]:
        once = canonical_sender(raw)
        assert canonical_sender(once) == once
