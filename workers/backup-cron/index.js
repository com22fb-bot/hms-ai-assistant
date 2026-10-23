// Dispara los respaldos de GitHub Actions desde el cron de Cloudflare (plan gratis).
const REPO = "com22fb-bot/hms-ai-assistant";
async function dispatch(env, wf) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "donexto-backup-cron",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  console.log(wf, r.status);
  if (r.status !== 204) throw new Error(`${wf} dispatch ${r.status}: ${await r.text()}`);
}
export default {
  async scheduled(event, env, ctx) {
    const day = new Date(event.scheduledTime).getUTCDay();
    await dispatch(env, "backup-daily.yml");
    if (day === 0) await dispatch(env, "backup-weekly.yml");
  },
};
