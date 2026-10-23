"""Backend del borrado: reporte fiel de Storage, reintentos y simulación (cliente simulado)."""
from app.api import admin_ops


class _Resp:
    def __init__(self, data): self.data = data


class _RPC:
    def __init__(self, c, name, args): self.c, self.name, self.args = c, name, args
    def execute(self):
        self.c.calls.append((self.name, self.args))
        if self.name in self.c.rpc_fail:
            raise RuntimeError("rpc")
        return _Resp(self.c.handlers[self.name](self.args))


class _Bucket:
    def __init__(self, c): self.c = c
    def remove(self, paths):
        self.c.removed_attempts.append(list(paths))
        if self.c.storage_fail:
            raise TimeoutError("storage")


class _Storage:
    def __init__(self, c): self.c = c
    def from_(self, name): return _Bucket(self.c)


class FakeDB:
    """Imita la cola SQL: pendiente → hecho/fallido; los reclamados no se reclaman de nuevo."""
    def __init__(self, n=0, storage_fail=False):
        self.queue = {i: {"id": i, "bucket": "attachments", "path": f"u/{i}.pdf", "status": "pendiente", "attempts": 0}
                      for i in range(1, n + 1)}
        self.storage_fail, self.rpc_fail = storage_fail, set()
        self.calls, self.removed_attempts = [], []
        self.storage = _Storage(self)
        self.handlers = {
            "admin_storage_purge_claim": self._claim, "admin_storage_purge_mark": self._mark,
            "admin_storage_purge_status": self._status, "admin_purge_user": self._purge}
        self.ready = set(self.queue)

    def rpc(self, name, args): return _RPC(self, name, args)

    def _claim(self, a):
        out = [dict(self.queue[i]) for i in sorted(self.ready)[: a["p_limit"]]]
        for r in out:
            self.queue[r["id"]]["attempts"] += 1
            self.ready.discard(r["id"])
        return out

    def _mark(self, a):
        for i in a["p_ids"]:
            q = self.queue[i]
            q["status"] = "hecho" if a["p_ok"] else ("fallido" if q["attempts"] >= 8 else "pendiente")
        return {}

    def _status(self, a):
        st = [q["status"] for q in self.queue.values()]
        return {k: st.count(k) for k in ("pendiente", "fallido", "hecho")}

    def _purge(self, a):
        base = {"rows_total": 10, "counts": {"profiles": 1}, "backup_counts": {}, "shared_kept": 1,
                "shared_accounts": [{"account_id": "x", "to_profile": "y", "kept_messages": 5}],
                "storage_queued": len(self.queue)}
        return {**base, "dry_run": True} if a["p_dry_run"] else {**base, "dry_run": False, "storage_paths": ["no-expone"]}

    def retry_window(self):  # simula que venció la espera exponencial
        self.ready = {i for i, q in self.queue.items() if q["status"] == "pendiente"}


def test_sin_archivos_es_completo():
    r = admin_ops.purge_response(admin_ops.purge_user_everything(FakeDB(0), "u"))
    assert r["status"] == "deleted" and r["complete"] is True


def test_storage_ok_es_completo_y_en_lotes():
    db = FakeDB(250)
    r = admin_ops.purge_response(admin_ops.purge_user_everything(db, "u"))
    assert r["status"] == "deleted" and r["complete"] is True
    assert r["storage"]["deleted"] == 250  # 2 lotes (200 + 50), bloques de 100 en Storage
    assert [len(x) for x in db.removed_attempts] == [100, 100, 50] and db._status({})["pendiente"] == 0


def test_fallo_storage_no_declara_exito():
    db = FakeDB(3, storage_fail=True)
    r = admin_ops.purge_response(admin_ops.purge_user_everything(db, "u"))
    assert r["status"] == "deleted_storage_pending" and r["complete"] is False
    assert r["storage"]["failed"] == 3 and "Storage" in r["message"]
    assert "storage_paths" not in r and "no-expone" not in str(r)


def test_reintento_recupera_y_termina_ok():
    db = FakeDB(3, storage_fail=True)
    admin_ops.purge_user_everything(db, "u")
    db.storage_fail = False
    db.retry_window()
    r = admin_ops.process_storage_queue(db)
    assert r["status"] == "ok" and r["deleted"] == 3 and db._status({})["hecho"] == 3


def test_reintentos_agotados_quedan_fallido_y_parcial():
    db = FakeDB(1, storage_fail=True)
    for _ in range(8):
        db.retry_window(); r = admin_ops.process_storage_queue(db)
    assert db.queue[1]["status"] == "fallido" and r["status"] == "parcial"
    db.retry_window(); assert admin_ops.process_storage_queue(db)["processed"] == 0  # no reintenta sin fin


def test_si_no_se_puede_marcar_no_es_exito():
    db = FakeDB(2); db.rpc_fail = {"admin_storage_purge_mark"}
    assert admin_ops.process_storage_queue(db)["status"] == "parcial"


def test_dry_run_no_toca_storage():
    db = FakeDB(4)
    r = admin_ops.purge_response(admin_ops.purge_user_everything(db, "u", dry_run=True))
    assert r["status"] == "dry_run" and r["storage_queued"] == 4 and r["shared_kept"] == 1
    assert db.removed_attempts == [] and ("admin_storage_purge_claim", {"p_limit": 200}) not in db.calls
    assert db.calls[0] == ("admin_purge_user", {"p_user": "u", "p_dry_run": True})
