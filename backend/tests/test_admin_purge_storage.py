from app.api import admin_ops


class _Bucket:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def remove(self, paths):
        if self.fail: raise RuntimeError("x")
        self.calls.append(list(paths))


class _Storage:
    def __init__(self, b): self.b = b
    def from_(self, name):
        assert name == "attachments"; return self.b


class _Client:
    def __init__(self, fail=False): self.bucket = _Bucket(fail); self.storage = _Storage(self.bucket)


def test_sin_archivos():
    assert admin_ops.purge_storage_paths(_Client(), [])["status"] == "sin_archivos"


def test_borra_en_lotes_de_100():
    c = _Client(); r = admin_ops.purge_storage_paths(c, [f"u/{i}" for i in range(250)] + ["", None])
    assert r == {"requested": 250, "deleted": 250, "failed": 0, "status": "ok"}
    assert [len(x) for x in c.bucket.calls] == [100, 100, 50]


def test_falla_storage_se_reporta_parcial():
    r = admin_ops.purge_storage_paths(_Client(fail=True), ["a"])
    assert r["status"] == "parcial" and r["failed"] == 1


def test_migracion_v2_incluye_buzones_conectados_y_rutas():
    sql = open("../supabase/migrations/20261023_002_admin_purge_user_v2.sql").read()
    assert "a.connected_by_profile_id = p_user" in sql
    assert "'storage_paths'" in sql
    assert "ux_comm_accounts_live_address_any" in sql
