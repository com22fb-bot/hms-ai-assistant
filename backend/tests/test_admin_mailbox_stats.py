from app.api.admin_ops import mailbox_stats_by_user, _empty_mail_stats


class _Resp:
    def __init__(self, data): self.data = data


class _Client:
    def __init__(self, data=None, fail=False): self.data, self.fail, self.calls = data, fail, []
    def rpc(self, name, params):
        self.calls.append((name, params)); outer = self
        class Q:
            def execute(self_inner):
                if outer.fail: raise RuntimeError("db down")
                return _Resp(outer.data)
        return Q()


def row(pid, aid, n, email="buzon@example.com", status="active", sync="2026-10-23T10:00:00Z"):
    return {"profile_id": pid, "account_id": aid, "provider": "gmail", "mailbox_email": email,
            "status": status, "last_sync_at": sync, "messages": n}


def test_sin_buzon_es_cero_real():
    stats = mailbox_stats_by_user(_Client([]), ["u1"])
    assert stats.get("u1", _empty_mail_stats(stats)) == {"messages_saved": 0, "mailboxes": [], "mail_counts_status": "ok"}


def test_buzon_vacio_cuenta_cero_con_desglose():
    s = mailbox_stats_by_user(_Client([row("u1", "a1", 0)]), ["u1"])
    assert s["u1"]["messages_saved"] == 0 and s["u1"]["mailboxes"][0]["messages"] == 0


def test_un_buzon():
    s = mailbox_stats_by_user(_Client([row("u1", "a1", 42)]), ["u1"])
    assert s["u1"]["messages_saved"] == 42 and len(s["u1"]["mailboxes"]) == 1


def test_varios_buzones_suma_y_desglose_ordenado():
    s = mailbox_stats_by_user(_Client([row("u1", "a1", 5), row("u1", "a2", 30, status=None)]), ["u1"])
    assert s["u1"]["messages_saved"] == 35
    assert [m["messages"] for m in s["u1"]["mailboxes"]] == [30, 5]
    assert s["u1"]["mailboxes"][0]["status"] == "desconocido"


def test_error_de_consulta_no_es_cero():
    stats = mailbox_stats_by_user(_Client(fail=True), ["u1"])
    assert stats == {"__error__": True}
    assert _empty_mail_stats(stats)["messages_saved"] is None


def test_aislamiento_entre_usuarios():
    c = _Client([row("u1", "a1", 7), row("u2", "a2", 9), row("intruso", "a3", 100)])
    s = mailbox_stats_by_user(c, ["u1", "u2"])
    assert s["u1"]["messages_saved"] == 7 and s["u2"]["messages_saved"] == 9 and "intruso" not in s
    assert c.calls == [("admin_mailbox_stats", {"p_profile_ids": ["u1", "u2"]})]  # una sola RPC, sin N+1


def test_nunca_devuelve_contenido():
    s = mailbox_stats_by_user(_Client([{**row("u1", "a1", 1), "subject": "x", "body_text": "y"}]), ["u1"])
    assert set(s["u1"]["mailboxes"][0]) == {"account_id", "provider", "email", "status", "last_sync_at", "messages"}
