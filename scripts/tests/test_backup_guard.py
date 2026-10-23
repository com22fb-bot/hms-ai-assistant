import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backup_guard import should_run, backup_job_ran
from backup_event_from_run import guard_skipped

T = "2026-10-23"
RAN = [{"name": "guard", "conclusion": "success"}, {"name": "backup", "conclusion": "success"}]
SKIP = [{"name": "guard", "conclusion": "success"}, {"name": "backup", "conclusion": "skipped"}]
def r(i, status="completed", concl="success", day=T, origen="cf-cron", event="workflow_dispatch"):
    t = "Donexto backup daily" + (f" [origen={origen}]" if origen else "")
    return {"id": i, "status": status, "conclusion": concl, "created_at": f"{day}T09:00:05Z", "display_title": t, "event": event}
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


class AstraOrigen(unittest.TestCase):
    """Los 6 casos de ASTRA (corrección del guard, 23-oct-2026)."""
    def test_1_manual_exitoso_no_bloquea_al_primer_cf_cron(self):
        self.assertTrue(should_run("workflow_dispatch", "cf-cron", 9, [r(1, origen="manual")], T, jobs({})))
    def test_1b_manual_exitoso_no_bloquea_al_schedule(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1, origen="manual")], T, jobs({})))
    def test_2_cf_cron_exitoso_deduplica_al_schedule(self):
        self.assertFalse(should_run("schedule", "", 9, [r(1, origen="cf-cron")], T, jobs({})))
    def test_3_cf_cron_duplicado_se_salta_y_schedule_deduplica_cf_cron(self):
        self.assertFalse(should_run("workflow_dispatch", "cf-cron", 9, [r(1, origen="cf-cron")], T, jobs({})))
        self.assertFalse(should_run("workflow_dispatch", "cf-cron", 9, [r(1, origen="schedule", event="schedule")], T, jobs({})))
    def test_4_automatica_en_vuelo_bloquea_pero_manual_en_vuelo_no(self):
        self.assertFalse(should_run("schedule", "", 9, [r(1, "in_progress", None, origen="cf-cron")], T, jobs({})))
        self.assertTrue(should_run("workflow_dispatch", "cf-cron", 9, [r(1, "in_progress", None, origen="manual")], T, jobs({})))
    def test_5_automatica_fallida_o_de_ayer_no_bloquea_reintento(self):
        self.assertTrue(should_run("schedule", "", 9, [r(1, concl="failure")], T, jobs({})))
        self.assertTrue(should_run("workflow_dispatch", "cf-cron", 9, [r(1, day="2026-10-22")], T, jobs({})))
    def test_6_error_de_api_falla_abierto(self):
        import io, contextlib, backup_guard as g
        os.environ["GITHUB_REPOSITORY"] = "x/y"
        def boom(*a, **k): raise RuntimeError("api caída")
        orig, g._gh_json_lines = g._gh_json_lines, boom
        argv, sys.argv = sys.argv, ["g", "backup-daily.yml", "workflow_dispatch", "9", "cf-cron"]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                g.main()
        finally:
            g._gh_json_lines, sys.argv = orig, argv
        self.assertEqual(buf.getvalue().strip(), "run=true")
    def test_legado_sin_etiqueta(self):
        from backup_guard import origin_of
        self.assertEqual(origin_of({"event": "schedule", "display_title": "Donexto backup daily"}), "schedule")
        self.assertEqual(origin_of({"event": "workflow_dispatch", "display_title": "Donexto backup daily"}), "manual")
    def test_run_name_del_workflow_coincide_con_el_parser(self):
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for wf in ("backup-daily.yml", "backup-weekly.yml"):
            txt = open(os.path.join(base, ".github", "workflows", wf)).read()
            self.assertIn("[origen=${{ github.event_name == 'schedule' && 'schedule' || (inputs.origen == 'cf-cron' && 'cf-cron' || 'manual') }}]", txt)
            self.assertIn("-r${{ github.run_id }}-a${{ github.run_attempt }}", txt)
        self.assertNotEqual(*[open(os.path.join(base, ".github", "workflows", w)).read().split("concurrency:")[1].split("\n")[0] for w in ("backup-daily.yml", "backup-weekly.yml")])

