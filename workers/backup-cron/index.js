// Dispara los respaldos de GitHub Actions desde el cron de Cloudflare (plan gratis).
// El Worker NO hace el respaldo (pg_dump + gpg + R2 necesitan un runner); solo lo dispara.
// Idempotencia: el schedule de GitHub (12:00 UTC) es el respaldo y se salta si ya hubo
// corrida exitosa/en curso ese día (scripts/backup_guard.py).
export const REPO = "com22fb-bot/hms-ai-assistant";

export async function dispatch(env, wf, { fetchImpl = fetch, sleep = (ms) => new Promise((r) => setTimeout(r, ms)), attempts = 3 } = {}) {
  let last = "";
  for (let i = 1; i <= attempts; i++) {
    try {
      const r = await fetchImpl(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "donexto-backup-cron",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ ref: "main" }),
      });
      if (r.status === 204) { console.log(JSON.stringify({ wf, ok: true, attempt: i })); return true; }
      last = `HTTP ${r.status}`;
      // 4xx (salvo 429) = config/permiso: no reintentar, fallar visible.
      if (r.status < 500 && r.status !== 429) break;
    } catch (e) {
      last = `red: ${e && e.name}`;
    }
    console.log(JSON.stringify({ wf, ok: false, attempt: i, error: last }));
    if (i < attempts) await sleep(1000 * 2 ** i);
  }
  throw new Error(`${wf} dispatch falló: ${last}`);
}

export function workflowsFor(scheduledTime) {
  // 09:00 UTC = 03:00 CDMX todo el año (México sin horario de verano desde oct 2022).
  const wfs = ["backup-daily.yml"];
  if (new Date(scheduledTime).getUTCDay() === 0) wfs.push("backup-weekly.yml");
  return wfs;
}

export default {
  async scheduled(event, env) {
    if (!env.GH_DISPATCH_TOKEN) throw new Error("falta GH_DISPATCH_TOKEN");
    // Diario y semanal independientes: la falla de uno no impide el otro.
    const res = await Promise.allSettled(workflowsFor(event.scheduledTime).map((wf) => dispatch(env, wf)));
    const bad = res.filter((r) => r.status === "rejected");
    if (bad.length) throw new Error(bad.map((b) => b.reason.message).join("; "));
  },
};
