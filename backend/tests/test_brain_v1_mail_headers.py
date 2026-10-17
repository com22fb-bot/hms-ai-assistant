"""Adenda 1.3 punto 5: cabeceras de lista y etiquetas del proveedor, una prueba por proveedor."""
import email
import inspect

from app.services.brain_v1.headers import gmail_mail_headers, graph_mail_headers, imap_mail_headers


def test_gmail_headers_and_labels():
    headers = [{"name": "From", "value": "x@y.com"},
               {"name": "List-Unsubscribe", "value": "<mailto:u@y.com>, <https://y.com/u>"},
               {"name": "List-Unsubscribe-Post", "value": "List-Unsubscribe=One-Click"},
               {"name": "list-id", "value": "Promos <promos.y.com>"}]
    out = gmail_mail_headers(headers, ["INBOX", "CATEGORY_PROMOTIONS", "INBOX"])
    assert out == {"list_unsubscribe": "<mailto:u@y.com>, <https://y.com/u>",
                   "list_unsubscribe_post": "List-Unsubscribe=One-Click",
                   "list_id": "Promos <promos.y.com>",
                   "provider_labels": ["INBOX", "CATEGORY_PROMOTIONS"], "source": "gmail"}


def test_graph_headers_and_labels():
    payload = {"internetMessageHeaders": [{"name": "List-Id", "value": "news.contoso.com"},
                                          {"name": "List-Unsubscribe", "value": "<https://c.com/u>"}],
               "categories": ["Azul"], "inferenceClassification": "other"}
    out = graph_mail_headers(payload)
    assert out["list_id"] == "news.contoso.com"
    assert out["list_unsubscribe"] == "<https://c.com/u>"
    assert out["list_unsubscribe_post"] is None
    assert out["provider_labels"] == ["Azul", "inference:other"]
    assert out["source"] == "graph"
    assert graph_mail_headers({})["provider_labels"] == []


def test_imap_headers_and_labels():
    raw = b"From: a@b.com\r\nList-Unsubscribe: <mailto:x@b.com>\r\nList-ID: <l.b.com>\r\nSubject: hi\r\n\r\nbody"
    out = imap_mail_headers(email.message_from_bytes(raw), "Bulk", ["\\Seen"])
    assert out["list_unsubscribe"] == "<mailto:x@b.com>"
    assert out["list_id"] == "<l.b.com>"
    assert out["provider_labels"] == ["folder:Bulk", "\\Seen"]
    assert out["source"] == "imap"


def test_inserts_only_write_mail_headers_behind_flag():
    from app.services import gmail_full_sync, gmail_sync, microsoft_import, yahoo_import
    for mod in (gmail_full_sync, gmail_sync):
        assert 'if brain_v1_enabled():\n                    message_payload["mail_headers"]' in inspect.getsource(mod)
    for mod in (microsoft_import, yahoo_import):
        assert '"mail_headers":' in inspect.getsource(mod)
        assert "if brain_v1_enabled() else {}" in inspect.getsource(mod)
    assert microsoft_import.MICROSOFT_SELECT.find("internetMessageHeaders") == -1
