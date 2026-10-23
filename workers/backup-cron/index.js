// Dispara los respaldos de GitHub Actions desde el cron de Cloudflare (plan gratis).
// El Worker NO hace el respaldo (pg_dump + gpg + R2 necesitan un runner); solo lo dispara.
// Idempotencia en dos capas:
//  1) Antes de reintentar, consulta si GitHub ya creó la corrida (respuesta perdida tras aceptar).
//  2) El workflow recibe origen=cf-cron y su guard (scripts/backup_guard.py) se salta si ya hubo
//     respaldo hoy; así un dispatch duplicado nunca produce doble respaldo.
export const REPO = "com22fb-bot/hms-ai-assistant";
const H = (env) => ({
  Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
  Accept: "application/vnd.github+json",
  "User-Agent": "donexto-backup-cron",
  "X-GitHub-Api-Version": "2022-11-28",
});

export async function alreadyCreated(env, wf, sinceIso, fetchImpl) {
  try {
    const r = await fetchImpl(
      `https://api.github.com/repos/${REPO}/actions/workflows/${wf}/runs?event=workflow_dispatch&created=%3E%3D${encodeURIComponent(sinceIso)}&per_page=10`,
      { headers: H(env) });
    if (r.status !== 200) return false;
    const d = await r.json();
    return (d.total_count || 0) > 0;
  } catch { return false; }
}

export async function dispatch(env, wf, { fetchImpl = fetch, sleep = (ms) => new Promise((r) => setTimeout(r, ms)), attempts = 3, now = () => Date.now() } = {}) {
  const since = new Date(now() - 60_000).toISOString().replace(/\.\d+Z$/, "Z");
  let last = "";
  for (let i = 1; i <= attempts; i++) {
    if (i > 1 && (await alreadyCreated(env, wf, since, fetchImpl))) {
      console.log(JSON.stringify({ wf, ok: true, attempt: i, note: "corrida ya creada; no se reintenta" }));
      return true;
    }
    try {
      const r = await fetchImpl(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
        method: "POST", headers: H(env),
        body: JSON.stringify({ ref: "main", inputs: { origen: "cf-cron" } }),
      });
      if (r.status === 204) { console.log(JSON.stringify({ wf, ok: true, attempt: i })); return true; }
      last = `HTTP ${r.status}`;
      if (r.status < 500 && r.status !== 429) break; // config/permiso: falla visible
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
    const res = await Promise.allSettled(workflowsFor(event.scheduledTime).map((wf) => dispatch(env, wf)));
    const bad = res.filter((r) => r.status === "rejected");
    if (bad.length) throw new Error(bad.map((b) => b.reason.message).join("; "));
  },
};
