import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backup_guard import should_run, backup_job_ran
from backup_event_from_run import guard_skipped

T = "2026-10-23"
RAN = [{"name": "guard", "conclusion": "success"}, {"name": "backup", "conclusion": "success"}]
SKIP = [{"name": "guard", "conclusion": "success"}, {"name": "backup", "conclusion": "skipped"}]
def r(i, status="completed", concl="success", day=T): return {"id": i, "status": status, "conclusion": concl, "created_at": f"{day}T09:00:05Z"}
def jobs(m): return lambda rid: m.get(rid, RAN)

class Guard(unittest.TestCase):
    def test_manual_siempre_corre(self):
        self.assertTrue(should_run("workflow_dispatch", "manual", 9, [r(1)], T, jobs({})))
        self.assertTrue(should_run("workflow_dispatch", "", 9, [r(1)], T, jobs({})))
    def test_schedule_salta_si_hubo_respaldo_real_hoy(self):
        self.assertFalse(should_run("schedule", "", 9, [r(1)], T, jobs({})))
    def test_cf_cron_duplicado_salta(self):
        self.assertFalse(should_run("workflow_dispatch", "cf-cron", 9, [r(1)], T, jobs({})))
    def test_exito_que_fue_saltado_no_cuenta(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1)], T, jobs({1: SKIP})))
    def test_corre_si_previa_fallo(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1, concl="failure")], T, jobs({})))
    def test_corre_si_no_hubo_nada(self):
        self.assertTrue(should_run("schedule", "", 9, [r(9, "in_progress", None)], T, jobs({})))
    def test_previa_en_vuelo_bloquea_todos_los_estados(self):
        for st in ("in_progress", "queued", "pending", "waiting", "requested"):
            self.assertFalse(should_run("schedule", "", 9, [r(1, st, None)], T, jobs({})), st)
    def test_posterior_en_cola_no_bloquea_evita_que_ambas_se_salten(self):
        self.assertTrue(should_run("workflow_dispatch", "cf-cron", 5, [r(9, "pending", None)], T, jobs({})))
    def test_exito_de_ayer_no_cuenta(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1, day="2026-10-22")], T, jobs({})))
    def test_cancelada_no_cuenta(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1, concl="cancelled")], T, jobs({})))
    def test_muchas_corridas_paginadas(self):
        runs = [r(i, concl="failure") for i in range(1, 250)] + [r(300)]
        self.assertFalse(should_run("schedule", "", 400, runs, T, jobs({})))
    def test_backup_job_ran(self):
        self.assertTrue(backup_job_ran(RAN)); self.assertFalse(backup_job_ran(SKIP)); self.assertFalse(backup_job_ran([]))
    def test_bitacora_ignora_corrida_saltada(self):
        self.assertTrue(guard_skipped({"jobs": SKIP})); self.assertFalse(guard_skipped({"jobs": RAN}))

if __name__ == "__main__": unittest.main()
