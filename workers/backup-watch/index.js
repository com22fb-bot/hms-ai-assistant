// 2º canal de alertas (independiente de GitHub Actions): corre en Cloudflare, lee R2 directo
// y avisa por Slack Y por Resend (cada uno de forma independiente; si uno cae, el otro sale).
// Casos: fresco -> silencio; viejo -> alerta; sin objetos -> alerta; R2 ilegible -> alerta.
export async function newestBackup(bucket, prefix = "db/") {
  let cursor, newest = null, count = 0;
  do {
    const page = await bucket.list({ prefix, cursor, limit: 1000 });
    for (const o of page.objects) {
      count++;
      if (!newest || o.uploaded > newest.uploaded) newest = o;
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return { newest, count };
}

export async function evaluate(env, now = Date.now()) {
  const maxH = Number(env.MAX_AGE_HOURS || "30");
  let res;
  try { res = await newestBackup(env.BACKUPS); }
  catch (e) { return { ok: false, reason: `R2 ilegible (${e && e.name})` }; }
  if (!res.newest) return { ok: false, reason: "no hay respaldos en db/" };
  const ageH = (now - new Date(res.newest.uploaded).getTime()) / 3.6e6;
  if (!(ageH <= maxH)) return { ok: false, reason: `último respaldo con ${ageH.toFixed(1)} h (máx ${maxH} h)`, key: res.newest.key };
  return { ok: true, ageH, key: res.newest.key };
}

async function slack(env, text, fetchImpl) {
  if (!env.SLACK_BOT_TOKEN) throw new Error("sin SLACK_BOT_TOKEN");
  const r = await fetchImpl("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.SLACK_BOT_TOKEN}`, "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ channel: env.SLACK_CHANNEL || "#alertas", text: `<!channel> ${text}` }),
  });
  const d = await r.json().catch(() => ({}));
  if (!d.ok) throw new Error(`slack ${r.status} ${d.error || ""}`.trim());
}

async function resend(env, text, fetchImpl) {
  if (!env.RESEND_API_KEY) throw new Error("sin RESEND_API_KEY");
  const r = await fetchImpl("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: env.ALERT_FROM, to: [env.ALERT_TO], subject: "Donexto: alerta de respaldos (Cloudflare)", text }),
  });
  if (r.status < 200 || r.status >= 300) throw new Error(`resend ${r.status}`);
}

export async function notify(env, text, fetchImpl = fetch) {
  const res = await Promise.allSettled([slack(env, text, fetchImpl), resend(env, text, fetchImpl)]);
  const sent = res.filter((r) => r.status === "fulfilled").length;
  console.log(JSON.stringify({ sent, errors: res.filter((r) => r.status === "rejected").map((r) => r.reason.message) }));
  if (!sent) throw new Error("ningún canal entregó la alerta");
  return sent;
}

export async function run(env, { now = Date.now(), fetchImpl = fetch } = {}) {
  const v = await evaluate(env, now);
  console.log(JSON.stringify(v));
  if (v.ok) return { ...v, sent: 0 };
  const tag = env.ALERT_TAG ? `[${env.ALERT_TAG}] ` : "";
  const sent = await notify(env, `${tag}:rotating_light: Donexto respaldos: ${v.reason}. Revisar Actions "Donexto backup daily" y R2 donexto-backups/db/. (aviso del Worker donexto-backup-watch, independiente de GitHub)`, fetchImpl);
  return { ...v, sent };
}

export default {
  async scheduled(event, env) { await run(env, { now: event.scheduledTime }); },
};
