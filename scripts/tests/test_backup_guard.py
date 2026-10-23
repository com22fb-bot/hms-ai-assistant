import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backup_guard import should_run
from backup_event_from_run import guard_skipped

T = "2026-10-23"
def r(i, status="completed", concl="success", day=T): return {"id": i, "status": status, "conclusion": concl, "created_at": f"{day}T09:00:05Z"}

class Guard(unittest.TestCase):
    def test_dispatch_siempre_corre(self):
        self.assertTrue(should_run("workflow_dispatch", 9, {"workflow_runs": [r(1)]}, T))
    def test_schedule_salta_si_ya_hubo_exito_hoy(self):
        self.assertFalse(should_run("schedule", 9, {"workflow_runs": [r(1), r(9, "in_progress", None)]}, T))
    def test_schedule_corre_si_cloudflare_fallo(self):
        self.assertTrue(should_run("schedule", 9, {"workflow_runs": [r(1, concl="failure"), r(9, "in_progress", None)]}, T))
    def test_schedule_corre_si_no_hubo_nada(self):
        self.assertTrue(should_run("schedule", 9, {"workflow_runs": [r(9, "in_progress", None)]}, T))
    def test_concurrencia_salta_si_otra_en_curso_o_cola(self):
        for st in ("in_progress", "queued", "pending", "waiting"):
            self.assertFalse(should_run("schedule", 9, {"workflow_runs": [r(1, st, None)]}, T))
    def test_exito_de_ayer_no_cuenta(self):
        self.assertTrue(should_run("schedule", 9, {"workflow_runs": [r(1, day="2026-10-22")]}, T))
    def test_cancelada_no_cuenta(self):
        self.assertTrue(should_run("schedule", 9, {"workflow_runs": [r(1, concl="cancelled")]}, T))
    def test_bitacora_ignora_corrida_saltada(self):
        self.assertTrue(guard_skipped({"jobs": [{"name": "guard", "conclusion": "success"}, {"name": "backup", "conclusion": "skipped"}]}))
        self.assertFalse(guard_skipped({"jobs": [{"name": "backup", "conclusion": "success"}]}))

if __name__ == "__main__": unittest.main()
